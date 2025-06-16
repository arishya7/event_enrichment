import requests
import json
from typing import Dict, Optional, List, Any
from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
from urllib.parse import unquote, urlparse
import re

# Load environment variables
load_dotenv()

def search_images(query: str, api_key: str, cx: str, num_results: int = 10, site_to_search: Optional[str] = None) -> Optional[List[str]]:
    if not api_key or not cx:
        print("Error: API Key or CX is missing for search_images call.")
        return None

    base_url = "https://www.googleapis.com/customsearch/v1"
    found_urls = set()

    exclude_sites = "lookaside OR sassymamasg OR honeykidsasia OR thesmartlocal OR theasianparent"



    num_site_results = num_results // 2
    num_general_results = num_results - num_site_results

    if site_to_search and site_to_search.lower() != 'null' and num_site_results > 0:
        try:
            netloc = urlparse(site_to_search).netloc
            if netloc:
                params = {
                    "key": api_key, "cx": cx, "q": query,
                    "searchType": "image", "num": num_site_results,
                    "siteSearch": netloc, "siteSearchFilter": "i",
                    "excludeTerms": exclude_sites
                }
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                for item in data.get("items", []):
                    found_urls.add(item['link'])
        except Exception as e:
            print(f"Site-restricted search failed: {e}")

    if num_general_results > 0:
        try:
            params = {
                "key": api_key, "cx": cx, "q": query,
                "searchType": "image", "num": num_general_results,
                "excludeTerms": exclude_sites
            }
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            initial_count = len(found_urls)
            for item in data.get("items", []):
                found_urls.add(item['link'])
        except Exception as e:
            print(f"Broad image search failed: {e}")

    if not found_urls:
        print("No images found from any source.")
        return None
    
    return list(found_urls)

def download_image(image_url: str, filepath: Path) -> Dict[str, str]:
    try:
        # Validate URL scheme
        if not urlparse(image_url).scheme in ('http', 'https'):
            return {}

        response = requests.get(image_url, stream=True, timeout=20)
        response.raise_for_status()

        # Extract source credit from URL
        try:
            parsed_url = urlparse(image_url)
            # Get domain without www. and .com/.org/etc
            domain = parsed_url.netloc.lower()
            domain = re.sub(r'^www\.', '', domain)  # Remove www.
            domain = re.sub(r'\.(com|org|net|edu|gov|sg|io|co|uk).*$', '', domain)  # Remove TLD
            # Convert dashes/underscores to spaces and capitalize words
            source_credit = ' '.join(word.capitalize() for word in re.split(r'[-_]', domain))
        except:
            source_credit = "Unknown Source"

        # Determine file extension from URL or content-type
        try:
            parsed_url = urlparse(image_url)
            url_path = Path(unquote(parsed_url.path))
            extension = url_path.suffix.lower() if url_path.suffix else '.jpg'
        except:
            extension = '.jpg'
        
        # Check content-type header to refine extension
        content_type = response.headers.get('content-type')
        if content_type:
            ct_lower = content_type.lower()
            if 'jpeg' in ct_lower and extension != ".jpg": 
                extension = ".jpg"
            elif 'png' in ct_lower and extension != ".png": 
                extension = ".png"
            elif 'gif' in ct_lower and extension != ".gif": 
                extension = ".gif"
            elif 'webp' in ct_lower and extension != ".webp": 
                extension = ".webp"
        
        # Add extension to filepath
        filepath = filepath.with_suffix(extension)
        filepath_name = str(filepath)
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
                
        result = {
            "local_path": str(filepath), 
            "original_url": image_url,
            "filename": filepath.name,
            "source_credit": source_credit
        }
        return result

    except requests.exceptions.HTTPError as e:
        return {}
    except requests.exceptions.Timeout:
        return {}
    except requests.exceptions.RequestException as e:
        print(f"    Error downloading image {image_url}: {e}")
        return {}
    except IOError as e:
        print(f"IO Error saving image to {filepath}: {e}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred for {image_url}: {e}")
        return {}

def main():
    print("--- Running image_extractor.py directly for testing ---")
    search_query = input("Enter a search query: ")
    site_to_search = input("Enter a site to search: ")
    print(search_images(search_query, api_key=os.getenv("GOOGLE_API_KEY"), cx=os.getenv("cx"), num_results=10, site_to_search=site_to_search))

if __name__ == "__main__":
    main()