from urllib.parse import urlparse, parse_qs
from typing import List
from html import unescape
import re
import json

from src.utils.config import config

def simple_text_to_id(text: str) -> str:
    """Convert text to a simple numeric id by summing character values"""
    return str(sum(ord(c) for c in text) % 10000000)  # Keep it to 7 digits

def extract_post_id(guid: str) -> int:
    try:
        parsed = urlparse(guid)
        query_params = parse_qs(parsed.query)
        if 'p' in query_params:
            return query_params['p'][0]
        else:
            parts = guid.split('/')
            if parts:
                last_part = parts[-1]
                try:
                    return str(int(last_part))
                except ValueError:
                    return simple_text_to_id(guid)
    except Exception:
        pass
    return "0"  # Return 0 for invalid GUIDs

def extract_post_id_atom(guid: str) -> int:
    try:
        parts = guid.split('/')
        if parts:
            last_part = parts[-1]
            try:
                return str(int(last_part))
            except ValueError:
                return simple_text_to_id(guid)
    except Exception:
        pass
    return "0"  # Return 0 for invalid GUIDs

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

def clean_text(text: str) -> str:
    """Clean text by removing problematic characters and normalizing whitespace."""
    if not isinstance(text, str):
        return text
    
    # First replace escaped characters
    text = text.replace('\\t', ' ').replace('\\n', ' ')
    
    # Then replace actual tab and newline characters
    text = text.replace('\t', ' ').replace('\n', ' ')
    
    # Remove a wider range of control characters except for common whitespace
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Replace multiple spaces with a single space and strip
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_urls(url: str) -> List[str]:
    # Pattern to match href attributes
    href_pattern = r'href=["\'](.*?)["\']'
    
    # Find all href URLs
    urls = re.findall(href_pattern, url)
    
    # Remove any tracking parameters
    clean_urls = []

    blog_ls =list(config.blog_website.__dict__.keys())
    for url in urls:
        if url.startswith('#') or any(blog in url for blog in blog_ls):
            continue
            
        # Remove tracking parameters
        base_url = url.split('?')[0]
        # Remove trailing punctuation
        base_url = base_url.rstrip('.,;:')
        if base_url and not base_url.startswith('#'):  # Only add non-empty URLs and non-anchor URLs
            clean_urls.append(base_url)
    
    return list(set(clean_urls))  # Remove duplicates

def is_valid_json(text: str) -> tuple[bool, str, any]:
    """Validates if a string is valid JSON and returns the parsed data.
    
    Args:
        text (str): The string to validate
        
    Returns:
        tuple[bool, str, any]: A tuple containing:
            - bool: Whether the string is valid JSON
            - str: Error message if invalid, empty string if valid
            - any: The parsed JSON data if valid, None if invalid
    """
    if not text or not isinstance(text, str):
        return False, "Input is empty or not a string", None
        
    try:
        # Try to parse the JSON
        data = json.loads(text)
        
        # Additional validation for your specific needs
        if isinstance(data, (list, dict)):
            return True, "", data
        else:
            return False, "JSON must be an object or array", None
            
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error while parsing JSON: {str(e)}", None

def preserve_links_html(html_text: str) -> str:
    """Clean HTML text while preserving links in format 'text [url]'."""
    # Remove CDATA sections
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', html_text)
    
    # Replace <a> tags with text [url] format
    def replace_link(match):
        tag = match.group(0)
        href = re.search(r'href=["\'](.*?)["\']', tag)
        if not href:
            return ''
        url = href.group(1)
        
        # Extract text between <a> and </a>
        text_match = re.search(r'>(.*?)</a>', tag)
        if not text_match:
            return url
        link_text = text_match.group(1)
        
        # Clean any nested HTML in the link text
        link_text = re.sub(r'<[^>]+>', ' ', link_text)
        link_text = unescape(link_text).strip()
        
        # Skip if it's just a "#" link or empty text
        if url.startswith('#') or not link_text:
            return link_text
            
        return f"{link_text} [{url}]"
    
    # Replace <a> tags first
    text = re.sub(r'<a[^>]+>.*?</a>', replace_link, text)
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Decode HTML entities
    text = unescape(text)
    
    # Remove extra whitespace and tabs
    text = re.sub(r'[\s\t]+', ' ', text)
    
    return text.strip()