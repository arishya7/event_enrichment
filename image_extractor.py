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

def search_images(query: str, api_key: str, cx: str, num_results: int = 10, site_to_search: Optional[str] = None) -> Optional[List[Dict]]:
    if not api_key or not cx: 
        print("Error: API Key or CX is missing for search_images call.") 
        return None
    
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "searchType": "image",
        "num": min(num_results, 10) 
    }

    if site_to_search.lower() != 'null':
        params["siteSearch"] = urlparse(site_to_search).netloc
        params["siteSearchFilter"] = "i" 
    
    response_obj = None
    try:
        response_obj = requests.get(base_url, params=params, timeout=10)
        response_obj.raise_for_status()  
        data = response_obj.json()
        return data.get("items", [])
    
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for query '{query}'")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error making request for query '{query}': {e}")
        if response_obj is not None and hasattr(response_obj, 'text'): print(f"Response content: {response_obj.text}")
        return None
    
    except json.JSONDecodeError as e:
        print(f"Error parsing response for query '{query}': {e}")
        if response_obj is not None and hasattr(response_obj, 'text'): print(f"Response content that failed to parse: {response_obj.text}")
        return None

def download_image(image_url: str, filepath: Path) -> Dict[str, str]:
    try:
        response = requests.get(image_url, stream=True, timeout=20)
        response.raise_for_status()

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
        final_filepath = filepath.with_suffix(extension)

        # Ensure directory exists
        final_filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(final_filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        
        local_path_str = str(final_filepath.relative_to(Path.cwd()) if final_filepath.is_absolute() else final_filepath)
        return {
            "local_path": local_path_str, 
            "original_url": image_url, 
            "filename": final_filepath.name
        }

    except requests.exceptions.Timeout:
        print(f"    Error: Timeout downloading image {image_url}")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"    Error downloading image {image_url}: {e}")
        return {}
    except IOError as e:
        print(f"    Error saving image {image_url} to {final_filepath}: {e}")
        return {}
    except Exception as e:
        print(f"    An unexpected error occurred while downloading/saving {image_url}: {e}")
        return {}

def main():
    return search_images("Art zone", api_key=os.getenv("GOOGLE_API_KEY"), cx=os.getenv("cx"), num_results=1, site_to_search="NULL")

if __name__ == "__main__":
    main()
