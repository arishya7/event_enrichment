"""
Category Page Scraper
Scrapes articles from category/listing pages and extracts events using Gemini.
Uses the same schema and output format as the RSS flow.

Supports:
- SassyMamaSG
- BYKidO
- SunnyCityKids
- LittleDayOut
- HoneyKidsAsia (single article mode)
"""

import json
import time
import os
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Load environment variables
load_dotenv()

# Default settings
DEFAULT_MAX_ARTICLES = 5
RATE_LIMIT = 2.0
GEMINI_MODEL = "gemini-2.0-flash"

# Paths to config files (same as RSS flow)
CONFIG_DIR = Path("config")
SCHEMA_FILE = CONFIG_DIR / "event_schema.json"
SYSTEM_INSTRUCTION_FILE = CONFIG_DIR / "system_instruction_w_schema.txt"


def load_system_instruction() -> str:
    """Load system instruction from config file."""
    if SYSTEM_INSTRUCTION_FILE.exists():
        with open(SYSTEM_INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # Fallback to basic instruction
        return """You are an event extraction specialist. Extract family-friendly events from the provided article content.
Return a JSON array of event objects. Each event should have all required fields from the schema."""


def load_event_schema() -> dict:
    """Load event schema from config file."""
    if SCHEMA_FILE.exists():
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


class CategoryScraper:
    """Scraper for category/listing pages. Uses same output format as RSS flow."""
    
    def __init__(self, url: str, max_articles: int = DEFAULT_MAX_ARTICLES, single_article_mode: bool = False):
        """
        Initialize the category scraper.
        
        Args:
            url: Category page URL or single article URL
            max_articles: Maximum number of articles to scrape
            single_article_mode: If True, treat URL as a single article
        """
        self.url = url
        self.max_articles = max_articles
        self.single_article_mode = single_article_mode
        self.output_dir = Path("data/events_output") / time.strftime("%Y%m%d_%H%M%S")
        self.events: List[Dict] = []
        self.system_instruction = load_system_instruction()
        self.event_schema = load_event_schema()
        
    def scrape(self) -> List[Dict]:
        """
        Main scraping method. Fetches category page, extracts article links, 
        and processes each article with Gemini.
        
        Returns:
            List of extracted event dictionaries
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright not available. Install with: pip install playwright && playwright install")
            return []
        
        print(f"\n{'='*60}")
        print("📂 CATEGORY PAGE SCRAPER")
        print(f"{'='*60}")
        print(f"URL: {self.url}")
        print(f"Max articles: {self.max_articles}")
        
        with sync_playwright() as p:
            print("\nLaunching browser...")
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            )
            
            # Step 1: Fetch category page
            print(f"\n📂 Fetching category page...")
            page = context.new_page()
            try:
                page.goto(self.url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                html = page.content()
            except Exception as e:
                print(f"❌ Error fetching page: {e}")
                context.close()
                browser.close()
                return []
            finally:
                page.close()
            
            # Check for Cloudflare block
            if "cloudflare" in html.lower() and "blocked" in html.lower():
                print("❌ Cloudflare is blocking access to this site.")
                print("   Try using RSS feed instead, or manually copy article URLs.")
                context.close()
                browser.close()
                return []
            
            # Step 2: Extract article links
            print(f"\n🔗 Extracting article links...")
            article_links = self._extract_article_links(html, self.url)
            
            if not article_links:
                print("❌ No article links found!")
                context.close()
                browser.close()
                return []
            
            print(f"\n✅ Found {len(article_links)} article links:")
            for i, url in enumerate(article_links, 1):
                print(f"   {i}. {url[:70]}...")
            
            # Step 3: Process each article
            print(f"\n📄 Processing articles with Gemini...")
            
            for i, article_url in enumerate(article_links, 1):
                print(f"\n📰 Article {i}/{len(article_links)}")
                print(f"   URL: {article_url[:60]}...")
                
                events = self._process_article(article_url, context)
                
                if events:
                    print(f"   ✅ Extracted {len(events)} events")
                    self.events.extend(events)
                else:
                    print(f"   ⚠️ No events extracted")
                
                if i < len(article_links):
                    time.sleep(RATE_LIMIT)
            
            context.close()
            browser.close()
        
        print(f"\n{'='*60}")
        print(f"✅ Total events extracted: {len(self.events)}")
        print(f"{'='*60}")
        
        return self.events
    
    def scrape_single_article(self, url: str) -> List[Dict]:
        """
        Scrape events from a single article URL.
        
        Args:
            url: Article URL
            
        Returns:
            List of extracted event dictionaries
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright not available.")
            return []
        
        print(f"\n{'='*60}")
        print("📄 SINGLE ARTICLE SCRAPER")
        print(f"{'='*60}")
        print(f"URL: {url}")
        
        with sync_playwright() as p:
            print("\nLaunching browser...")
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            )
            
            events = self._process_article(url, context)
            
            context.close()
            browser.close()
        
        self.events = events
        return events
    
    def _extract_article_links(self, html: str, base_url: str) -> List[str]:
        """Extract article links from a category page."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        base_domain = urlparse(base_url).netloc
        seen = set()
        
        # Skip patterns
        skip_patterns = ['/category/', '/tag/', '/tagged/', '/author/', '/page/', '#', 
                        '/directory/', '/schools/', '/podcast', '/privacy', '/contact',
                        '/about', '/advertise', 'javascript:', 'mailto:', '/feed/',
                        '/pregnancy/', '/travel/', '/shop/', '/cart/', '/account/',
                        '/collections/', '/products/', '/pages/',
                        'facebook.com', 'instagram.com', 'youtube.com', 'tiktok.com', 'telegram',
                        'trip.com', 'klook.com', 'foodpanda', 
                        'preschool', 'kindergarten', 'open-house', 'school-holiday']
        
        print("   Looking for article headings...")
        
        for heading in soup.find_all(['h3', 'h2']):
            a = heading.find('a', href=True)
            if not a:
                parent_a = heading.find_parent('a', href=True)
                if parent_a:
                    a = parent_a
                else:
                    continue
                
            href = a['href'].strip()
            full_url = urljoin(base_url, href)
            
            if full_url in seen:
                continue
            if urlparse(full_url).netloc != base_domain:
                continue
            if any(p in full_url.lower() for p in skip_patterns):
                continue
            
            path = urlparse(full_url).path.lower()
            
            # Site-specific patterns
            is_bykido = '/blogs/' in path and '/tagged/' not in path and len(path) > 35
            is_sassymama = 'sassymama' in base_domain and len(path) > 15
            is_sunnycity = 'sunnycitykids' in base_domain and ('/activities/' in path or '/blog/' in path) and len(path) > 15
            is_littledayout = 'littledayout' in base_domain and '/category/' not in path and len(path) > 10 and '-' in path
            
            if is_bykido or is_sassymama or is_sunnycity or is_littledayout:
                heading_text = heading.get_text().strip()[:60]
                print(f"      Found: {heading_text}...")
                
                seen.add(full_url)
                links.append(full_url)
                
                if len(links) >= self.max_articles:
                    return links
        
        print(f"   Found {len(links)} articles from headings")
        return links
    
    def _process_article(self, url: str, context) -> List[Dict]:
        """Fetch and process a single article."""
        try:
            # Fetch article content
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()
            page.close()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract title
            title = ""
            title_tag = soup.find('h1')
            if title_tag:
                title = title_tag.get_text().strip()
            
            print(f"   Title: {title[:50]}..." if title else "   Title: (not found)")
            
            # Extract main content
            content = ""
            for selector in ['article', '.post-content', '.entry-content', '.article-content', 'main']:
                container = soup.select_one(selector)
                if container:
                    for script in container(['script', 'style', 'nav', 'header', 'footer']):
                        script.decompose()
                    content = container.get_text(separator=' ', strip=True)
                    if len(content) > 500:
                        break
            
            # Extract images from article
            images = self._extract_images(soup, url)
            
            print(f"   Content length: {len(content)} chars")
            print(f"   Images found: {len(images)}")
            
            if len(content) < 100:
                print("   ⚠️ Content too short, skipping...")
                return []
            
            # Extract events with Gemini (using full schema)
            return self._extract_events_with_gemini(title, content, url, images)
            
        except Exception as e:
            print(f"   ❌ Error processing article: {e}")
            return []
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract images from article."""
        images = []
        seen_urls = set()
        
        # Look for images in article content
        for img in soup.find_all('img', src=True):
            src = img.get('src', '')
            if not src or src in seen_urls:
                continue
            
            # Skip small icons, logos, avatars
            if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'gravatar', 'emoji', 'pixel', '1x1']):
                continue
            
            # Make absolute URL
            full_url = urljoin(base_url, src)
            
            # Only include image file types
            if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                seen_urls.add(full_url)
                images.append({
                    "url": full_url,
                    "alt": img.get('alt', '')
                })
        
        return images[:10]  # Limit to first 10 images
    
    def _extract_events_with_gemini(self, title: str, content: str, article_url: str, images: List[Dict]) -> List[Dict]:
        """Use Gemini to extract events from article content using the full schema."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("   ⚠️ GOOGLE_API_KEY not found!")
            return []
        
        client = genai.Client(api_key=api_key)
        
        # Build image context (minimal to save tokens)
        image_context = ""
        if images:
            image_context = "\n\nImages: " + ", ".join([img['url'] for img in images[:5]])
        
        all_events = []
        
        # Step 1: First, ask Gemini how many events are in the article
        count = self._count_events(client, title, content)
        print(f"   📊 Estimated events in article: {count}")
        
        if count <= 10:
            # Small article - extract all at once
            all_events = self._call_gemini_batch(client, title, content, article_url, image_context, 1, count)
        else:
            # Large article - extract in batches of 8
            BATCH_SIZE = 8
            num_batches = (count + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"   📦 Extracting in {num_batches} batches of {BATCH_SIZE}...")
            
            for batch in range(num_batches):
                start = batch * BATCH_SIZE + 1
                end = min((batch + 1) * BATCH_SIZE, count)
                print(f"   📝 Batch {batch + 1}/{num_batches}: events {start}-{end}...")
                
                batch_events = self._call_gemini_batch(client, title, content, article_url, image_context, start, end)
                if batch_events:
                    all_events.extend(batch_events)
                    print(f"      ✅ Got {len(batch_events)} events")
                else:
                    print(f"      ⚠️ No events from this batch")
                
                time.sleep(0.5)  # Rate limit between batches
        
        # Post-process events to ensure required fields
        processed_events = []
        seen_titles = set()
        
        for event in all_events:
            # Deduplicate by title
            event_title = event.get('title', '')
            if event_title in seen_titles:
                continue
            seen_titles.add(event_title)
            
            # Ensure guid and url are set
            if not event.get('guid'):
                event['guid'] = article_url
            if not event.get('url'):
                event['url'] = article_url
            
            # Ensure images array exists
            if 'images' not in event:
                event['images'] = []
            
            # Add source tracking
            event['_source_article'] = article_url
            event['_source_title'] = title
            
            processed_events.append(event)
        
        return processed_events
    
    def _count_events(self, client, title: str, content: str) -> int:
        """Ask Gemini to count how many events/venues are in the article."""
        # Use full content for accurate count
        prompt = f"""Article: {title}

Content:
{content[:30000]}

---
This article lists multiple events, venues, restaurants, playgrounds, or attractions.
Count the TOTAL number of separate items/places mentioned.
Look for numbered lists, headings, or sections that indicate individual venues.
Return ONLY a single number. Example: 72"""

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=20,
                )
            )
            # Extract number from response
            import re
            numbers = re.findall(r'\d+', response.text.strip())
            if numbers:
                count = int(numbers[0])
                return min(count, 100)  # Cap at 100 to be safe
            return 15
        except:
            return 15  # Default estimate
    
    def _call_gemini_batch(self, client, title: str, content: str, article_url: str, image_context: str, start: int, end: int) -> List[Dict]:
        """Extract a specific range of events from the article."""
        prompt = f"""Article: {title}
URL: {article_url}

Content:
{content[:25000]}
{image_context}
---
Extract ONLY events #{start} to #{end} from this article.
- If article lists "10 Best Restaurants", and I ask for #1-#3, return only the first 3.
- description: 150-250 chars MAX
- blurb: 30-50 chars  
- Return empty array [] if these event numbers don't exist

Return JSON array with these events only."""

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2,
                    max_output_tokens=8000,  # Set explicit limit
                )
            )
            
            text = response.text.strip()
            
            # Clean up markdown code blocks
            if text.startswith("```"):
                lines = text.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                text = '\n'.join(lines)
            
            # Try to fix truncated JSON
            text = self._fix_truncated_json(text)
            
            events = json.loads(text)
            
            if isinstance(events, dict):
                events = [events]
            
            return events
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error: {e}")
            # Try to extract complete events from partial response
            try:
                events = self._extract_complete_events(text)
                if events:
                    print(f"   ✅ Recovered {len(events)} events from partial response")
                    return events
            except:
                pass
            return []
        except Exception as e:
            print(f"   ⚠️ Gemini error: {e}")
            return []
    
    def _fix_truncated_json(self, text: str) -> str:
        """Try to fix truncated JSON by closing open brackets."""
        if not text:
            return "[]"
        
        # Count brackets
        open_brackets = text.count('[') - text.count(']')
        open_braces = text.count('{') - text.count('}')
        
        # If balanced, return as-is
        if open_brackets == 0 and open_braces == 0:
            return text
        
        # Try to find last complete object
        # Look for last complete "}" that's part of an object in array
        last_complete = text.rfind('},')
        if last_complete > 0:
            text = text[:last_complete + 1] + ']'
            return text
        
        # Just close brackets
        text = text.rstrip(',\n\r\t ')
        text += '}' * open_braces + ']' * open_brackets
        return text
    
    def _extract_complete_events(self, text: str) -> List[Dict]:
        """Extract complete event objects from partial JSON response."""
        import re
        events = []
        
        # Find all complete JSON objects
        # Match { ... } patterns that look complete
        pattern = r'\{[^{}]*"title"[^{}]*"venue_name"[^{}]*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                event = json.loads(match)
                if event.get('title') and event.get('venue_name'):
                    events.append(event)
            except:
                continue
        
        return events
    
    def save_events(self, events: Optional[List[Dict]] = None) -> Path:
        """Save extracted events to JSON file (same format as RSS flow)."""
        events = events or self.events
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine source name from URL
        domain = urlparse(self.url).netloc
        source_name = domain.replace('www.', '').split('.')[0]
        
        output_file = self.output_dir / f"{source_name}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Saved {len(events)} events to: {output_file}")
        return output_file
