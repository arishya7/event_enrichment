import xml.etree.ElementTree as ET
import re
from typing import Dict, List
from html import unescape
import os
import json
from datetime import datetime

def clean_html(html_text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    # Remove CDATA sections
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Decode HTML entities
    text = unescape(text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_urls(text: str) -> List[str]:
    """Extract URLs from href attributes only, excluding internal anchors and specific domains."""
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

def parse_rss_file(file_path: str) -> List[Dict]:
    """Parse RSS XML file and extract required information."""
    try:
        # Parse XML file directly
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        articles = []
        
        # Find all item elements
        for item in root.findall('.//item'):
            # Extract title
            title = clean_html(item.findtext('title', ''))
            
            # Extract content
            content = clean_html(item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded', ''))
            
            # Extract author
            author = clean_html(item.findtext('{http://purl.org/dc/elements/1.1/}creator', ''))
            
            # Extract publication date
            pub_date = item.findtext('pubDate', '')
            
            # Extract categories
            categories = [clean_html(cat.text) for cat in item.findall('category')]
            
            # Extract all URLs
            all_text = ET.tostring(item, encoding='unicode')
            urls = extract_urls(all_text)
            
            # Create article dictionary
            article = {
                'title': title,
                'author': author,
                'publication_date': pub_date,
                'categories': categories,
                'content': content,
                'urls': urls
            }
            
            articles.append(article)
        
        return articles
    
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def save_to_json(articles: List[Dict], output_file: str):
    """Save articles to a JSON file."""
    # Create output directory if it doesn't exist
    os.makedirs('RSS_output', exist_ok=True)
    
    # Add timestamp to the data
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'article_count': len(articles),
        'articles': articles
    }
    
    # Save to file
    output_path = os.path.join('RSS_output', output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(articles)} articles to {output_path}")

def main():
    # Process XML files from test_RSS directory
    file_mapping = {
        'RSS_test/theasianparent.xml': 'theasianparent.json',
        'RSS_test/sassymamasg.xml': 'sassymamasg.json'
    }
    
    for input_file, output_file in file_mapping.items():
        if not os.path.exists(input_file):
            print(f"File {input_file} not found")
            continue
            
        print(f"\nProcessing {input_file}:")
        print("-" * 50)
        
        articles = parse_rss_file(input_file)
        save_to_json(articles, output_file)

if __name__ == "__main__":
    main() 