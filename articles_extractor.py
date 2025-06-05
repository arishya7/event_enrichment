import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Set
from html import unescape
import os
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from bisect import bisect_left
import requests

class GuidDatabase:
    def __init__(self, blog_name: str, database_dir: Path):
        self.blog_name = blog_name
        self.database_path = database_dir / f"{blog_name}_guids.json"
        self.guids = self._load_sorted_guids()
    
    def _load_sorted_guids(self) -> List[int]:
        if self.database_path.exists():
            with open(self.database_path, 'r', encoding='utf-8') as f:
                # Convert stored strings to integers
                return [int(guid) for guid in json.load(f)]
        return []
    
    def save(self):
        with open(self.database_path, 'w', encoding='utf-8') as f:
            # Convert integers to strings for JSON storage
            json.dump([str(guid) for guid in self.guids], f, indent=2)
    
    def contains(self, guid: int) -> bool:
        i = bisect_left(self.guids, guid)
        return i != len(self.guids) and self.guids[i] == guid
    
    def add_many(self, new_guids: List[int]):
        for guid in new_guids:
            if not self.contains(guid):
                i = bisect_left(self.guids, guid)
                self.guids.insert(i, guid)

class MetaDatabase:
    def __init__(self):
        self.meta_dir = Path('meta_database')
        self.meta_dir.mkdir(exist_ok=True)
        self.guid_dir = self.meta_dir / 'guid_database'
        self.guid_dir.mkdir(exist_ok=True)
        self.history_file = self.meta_dir / 'articles_extractor_history.json'
        # Initialize current run data
        self.current_run = {
            'timestamp': datetime.now().isoformat(),
            'blogs_processed': []
        }
        # Cache for GUID databases
        self.guid_databases = {}
        
    def get_guid_database(self, blog_name: str) -> GuidDatabase:
        if blog_name not in self.guid_databases:
            self.guid_databases[blog_name] = GuidDatabase(blog_name, self.guid_dir)
        return self.guid_databases[blog_name]
            
    def load_history(self) -> List[Dict]:
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def add_blog_to_current_run(self, blog_name: str, total_articles: int, 
                               new_articles: int, repeated_articles: int, 
                               new_guids: List[str]):
        blog_data = {
            'blog_name': blog_name,
            'total_articles_processed': total_articles,
            'new_articles_extracted': new_articles,
            'repeated_articles': repeated_articles,
            'new_article_guids': [str(x) for x in sorted(int(guid) for guid in new_guids)]
        }
        self.current_run['blogs_processed'].append(blog_data)
    
    def save_current_run(self):
        # Save all GUID databases - they maintain their own sorted order
        for guid_db in self.guid_databases.values():
            guid_db.save()
            
        # Save extraction history
        history = self.load_history()
        history.append(self.current_run)
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
            
        # Reset current run
        self.current_run = {
            'timestamp': datetime.now().isoformat(),
            'blogs_processed': []
        }

def extract_rss_feed(blog_url: str, filename: str):
    # Define headers to mimic a real browser (will only use if needed)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1'  # Do Not Track
    }

    # List of possible feed URL formats to try
    feed_formats = [
        f"https://{blog_url}",  # Original format
        f"https://{blog_url.replace('/feed/', '')}/feed",  # Without trailing slash
        f"https://{blog_url.replace('/feed', '')}/feed",   # Different feed path
        f"https://{blog_url.split('/')[0]}/feed"          # Root feed
    ]
    output_path = os.path.join('RSS_temp', filename)
    last_error = None
    for feed_url in feed_formats:
        try:
            
            # First try without headers
            try:
                response = requests.get(feed_url, timeout=10)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    print("Got 403 error, retrying with browser headers...")
                    response = requests.get(feed_url, headers=headers, timeout=10)
                    response.raise_for_status()
                else:
                    raise e

            # Check if response is actually RSS/XML content
            if 'xml' in response.headers.get('Content-Type', '').lower() or '<?xml' in response.text[:100]:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                return output_path
            else:
                print(f"URL {feed_url} returned non-XML content, try another format")
                
        except requests.RequestException as e:
            print(f"Failed to fetch {feed_url}: {str(e)}")
            last_error = e
            continue
        except Exception as e:
            print(f"Unexpected error with {feed_url}: {str(e)}")
            last_error = e
            continue

    # If we get here, none of the formats worked
    if last_error:
        print(f"Error: Could not fetch RSS feed from any URL format for {blog_url}: {str(last_error)}")
    else:
        print(f"Error: Could not find valid RSS feed for {blog_url}")
    return False

def extract_post_id(guid: str) -> int:
    try:
        parsed = urlparse(guid)
        query_params = parse_qs(parsed.query)
        if 'p' in query_params:
            return int(query_params['p'][0])
    except Exception:
        pass
    return 0  # Return 0 for invalid GUIDs

def clean_html(html_text: str) -> str:
    # Remove CDATA sections
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    text = unescape(text)
    # Remove extra whitespace and tabs
    text = re.sub(r'[\s\t]+', ' ', text)
    
    return text.strip()

def extract_urls(text: str) -> List[str]:
    # Pattern to match href attributes
    href_pattern = r'href=["\'](.*?)["\']'
    
    # Find all href URLs
    urls = re.findall(href_pattern, text)
    
    # Remove any tracking parameters
    clean_urls = []
    for url in urls:
        # Skip URLs that start with # or contain sassymamasg
        if url.startswith('#') or 'sassymamasg' in url or 'theasianparent' in url:
            continue
            
        # Remove tracking parameters
        base_url = url.split('?')[0]
        # Remove trailing punctuation
        base_url = base_url.rstrip('.,;:')
        if base_url and not base_url.startswith('#'):  # Only add non-empty URLs and non-anchor URLs
            clean_urls.append(base_url)
    
    return list(set(clean_urls))  # Remove duplicates

def parse_rss_file(file_path: str, blog_name: str, meta_db: MetaDatabase) -> List[Dict]:
    try:
        # Get GUID database for this blog
        guid_db = meta_db.get_guid_database(blog_name)
        
        # Parse XML file directly
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        articles = []
        new_guids = []
        total_articles = 0
        repeated_articles = 0
        
        # Find all item elements
        for item in root.findall('.//item'):
            total_articles += 1
            
            # Extract GUID first and get post ID as integer
            guid = item.findtext('guid', '')
            post_id = extract_post_id(guid)
            
            # Skip if post ID is 0 (invalid) or already exists in database
            if post_id == 0 or guid_db.contains(post_id):
                repeated_articles += 1
                continue
                
            # Add to new GUIDs list
            new_guids.append(post_id)
            
            # Extract other fields
            title = clean_html(item.findtext('title', ''))
            content = clean_html(item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded', ''))
            author = clean_html(item.findtext('{http://purl.org/dc/elements/1.1/}creator', ''))
            categories = [clean_html(cat.text) for cat in item.findall('category')]
            all_text = ET.tostring(item, encoding='unicode')
            urls = extract_urls(all_text)

            # Create article dictionary
            article = {
                'title': title,
                'author': author,
                'categories': categories,
                'content': content,
                'urls': urls,
                'guid': guid,
                'post_id': str(post_id)  # Store as string in output for consistency
            }
            
            articles.append(article)
        
        # Update GUID database with new GUIDs
        guid_db.add_many(new_guids)
        
        # Add blog data to current run
        meta_db.add_blog_to_current_run(
            blog_name=blog_name,
            total_articles=total_articles,
            new_articles=len(articles),
            repeated_articles=repeated_articles,
            new_guids=[str(x) for x in sorted(new_guids)]  # Convert to strings for JSON output
        )
        
        return articles
    
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def save_to_json(articles: List[Dict], output_file: str):
    # Create output directory if it doesn't exist
    os.makedirs('articles_output', exist_ok=True)
    
    # Save to file
    output_path = os.path.join('articles_output', output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(articles)} articles to {output_path}")
    return output_path

def main():
    """Test articles extraction with user control"""
    print("=== Articles Extractor Test ===\n")
    
    # Read blog URLs and create blog dictionary
    try:
        with open("blog_websites.txt", "r") as f:
            blog_dict = {}
            for line in f:
                if line.strip():
                    blog_url, blog_name = line.strip().split(",")
                    blog_dict[blog_name] = {"blog_url": blog_url}
    except FileNotFoundError:
        print("❌ Error: blog_websites.txt not found")
        return
    except Exception as e:
        print(f"❌ Error reading blog_websites.txt: {e}")
        return
        
    # Show available blogs
    print("📚 Available blogs:")
    for i, (blog_name, _) in enumerate(blog_dict.items(), 1):
        print(f"   {i}. {blog_name}")
    
    # User selection for blog
    while True:
        try:
            choice = input(f"\nSelect blog (1-{len(blog_dict)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return
                
            blog_index = int(choice) - 1
            if 0 <= blog_index < len(blog_dict):
                selected_blog_name = list(blog_dict.keys())[blog_index]
                selected_blog = blog_dict[selected_blog_name]
                break
            else:
                print(f"❌ Please enter a number between 1 and {len(blog_dict)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q'")
    
    # Create RSS_temp directory
    os.makedirs('RSS_temp', exist_ok=True)
    
    # Extract RSS feed
    print(f"\n📥 Extracting RSS feed for {selected_blog_name}...")
    filename = f"{selected_blog_name}.xml"
    rss_path = extract_rss_feed(selected_blog['blog_url'], filename)
    
    if not rss_path:
        print("❌ Failed to extract RSS feed")
        return
    print("✅ RSS feed extracted successfully")
    
    # Initialize MetaDatabase
    meta_db = MetaDatabase()
    
    # Get user input for number of articles
    while True:
        try:
            print("\nHow many articles do you want to extract?")
            print("1. All new articles")
            print("2. Specify number")
            print("3. Quit")
            
            option = input("Select option (1-3): ").strip()
            
            if option == '3':
                return
            elif option == '1':
                num_articles = None  # Will extract all new articles
                break
            elif option == '2':
                num = input("Enter number of articles to extract: ").strip()
                num_articles = int(num)
                if num_articles <= 0:
                    print("❌ Please enter a positive number")
                    continue
                break
            else:
                print("❌ Please enter 1, 2, or 3")
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Parse RSS and extract articles
    print(f"\n📝 Extracting articles from RSS feed...")
    articles = parse_rss_file(rss_path, selected_blog_name, meta_db)
    
    if not articles:
        print("❌ No new articles found")
        return
    
    # Limit articles if specified
    if num_articles is not None:
        articles = articles[:num_articles]
    
    # Save articles
    articles_filename = f"{selected_blog_name}_articles.json"
    output_path = save_to_json(articles, articles_filename)
    
    # Save metadata
    meta_db.save_current_run()
    
    print("\n✨ Summary:")
    print(f"📊 Total articles extracted: {len(articles)}")
    print(f"💾 Articles saved to: {output_path}")
    
if __name__ == "__main__":
    main() 