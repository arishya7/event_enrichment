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
import cloudscraper

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
    # Define headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1'  # Do Not Track
    }

    output_path = os.path.join('RSS_temp', filename)
    scraper = cloudscraper.create_scraper()
    response = None

    try:
        # First, try without custom headers
        print(f"Attempting to fetch {blog_url} without headers...")
        response = scraper.get(blog_url, timeout=15)
        response.raise_for_status()
        print("Successfully fetched on the first attempt.")
    
    except requests.RequestException as e:
        # If it fails (e.g., 403 Forbidden), try again with headers
        if response is not None and 400 <= response.status_code < 500:
            print(f"Initial request failed with status {response.status_code}. Retrying with headers...")
            try:
                response = scraper.get(blog_url, headers=headers, timeout=15)
                response.raise_for_status()
                print("Successfully fetched with headers.")
            except requests.RequestException as e2:
                print(f"Error: Failed to fetch {blog_url} even with headers. Reason: {str(e2)}")
                return False
        else:
            # Handle other request exceptions (connection errors, timeouts, etc.)
            print(f"Error: Failed to fetch {blog_url}. Reason: {str(e)}")
            return False

    # If we have a successful response from either attempt, process it
    try:
        content_type = response.headers.get('Content-Type', '').lower()
        is_xml_content_type = 'xml' in content_type
        is_xml_declaration = response.text.lstrip().startswith('<?xml')
        
        if is_xml_content_type or is_xml_declaration:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text.strip())
            print(f"Successfully fetched and saved RSS feed from {blog_url}")
            return output_path
        else:
            print(f"Error: URL {blog_url} returned non-XML content (Content-Type: {content_type}).")
            return False
            
    except Exception as e:
        print(f"An unexpected error occurred with {blog_url} while processing the response: {str(e)}")
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
    # Load blog websites and get blog names to filter
    blog_names = []
    try:
        with open('blog_websites.txt', 'r') as f:
            for line in f:
                blog_name = line.strip().split(',')[1]
                blog_names.append(blog_name)
    except Exception as e:
        print(f"Error loading blog_websites.txt: {e}")
        
    for url in urls:
        # Skip URLs that start with # or contain blog names
        if url.startswith('#') or any(blog in url for blog in blog_names):
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
            article_website = item.findtext('link', '')
            

            # Create article dictionary
            article = {
                'title': title,
                'author': author,
                'categories': categories,
                'content': content,
                'urls': urls,
                'guid': guid,
                'post_id': str(post_id),  # Store as string in output for consistency
                'article_website': article_website
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
    blog_keys = list(blog_dict.keys())
    for i, blog_name in enumerate(blog_keys, 1):
        print(f"   {i}. {blog_name}")
    print(f"   {len(blog_keys) + 1}. ALL BLOGS")

    # User selection for blog
    blogs_to_process = []
    while True:
        try:
            choice = input(f"\nSelect an option (1-{len(blog_keys) + 1}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(blog_keys):
                selected_blog_name = blog_keys[choice_num - 1]
                blogs_to_process.append(selected_blog_name)
                break
            elif choice_num == len(blog_keys) + 1:
                blogs_to_process = blog_keys
                print("✅ Selected to process ALL blogs.")
                break
            else:
                print(f"❌ Please enter a number between 1 and {len(blog_keys) + 1}")
        except ValueError:
            print("❌ Please enter a valid number or 'q'")

    # Create RSS_temp directory
    os.makedirs('RSS_temp', exist_ok=True)
    meta_db = MetaDatabase()
    total_extracted_count = 0

    # Get user input for number of articles
    while True:
        try:
            print("\nHow many articles do you want to extract per blog?")
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

    # --- Process all selected blogs ---
    for i, blog_name in enumerate(blogs_to_process, 1):
        print(f"\n--- Processing Blog {i}/{len(blogs_to_process)}: {blog_name} ---")
        blog_info = blog_dict[blog_name]
        
        # Extract RSS feed
        print(f"📥 Extracting RSS feed for {blog_name}...")
        filename = f"{blog_name}.xml"
        rss_path = extract_rss_feed(blog_info['blog_url'], filename)
        
        if not rss_path:
            print(f"❌ Failed to extract RSS feed for {blog_name}. Skipping.")
            continue
        print("✅ RSS feed extracted successfully.")
        
        # Parse RSS and extract articles
        print(f"📝 Extracting articles from RSS feed...")
        articles = parse_rss_file(rss_path, blog_name, meta_db)
        
        if not articles:
            print(f"ℹ️ No new articles found for {blog_name}.")
            continue
        
        # Limit articles if specified
        if num_articles is not None:
            articles = articles[:num_articles]
        
        # Save articles
        articles_filename = f"{blog_name}_articles.json"
        output_path = save_to_json(articles, articles_filename)
        total_extracted_count += len(articles)

    # Save metadata for the entire run
    meta_db.save_current_run()
    
    print("\n\n======= ✨ Overall Summary ✨ =======")
    print(f"🔄 Processed {len(blogs_to_process)} blog(s).")
    print(f"📊 Total new articles extracted: {total_extracted_count}")
    print(f"✅ See 'articles_output' for JSON files and 'meta_database' for history.")
    
if __name__ == "__main__":
    main() 