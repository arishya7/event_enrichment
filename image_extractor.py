import requests
import json
from typing import Dict, Optional, List, Any
from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
from urllib.parse import unquote, urlparse

# Load environment variables
load_dotenv()

class GoogleCustomSearchAPI:
    def __init__(self):
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.api_key = os.getenv("GOOGLE_API_KEY") 
        self.cx = os.getenv("cx") 
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file for Custom Search.")
        if not self.cx:
            raise ValueError("CX (Custom Search Engine ID) is not set in .env file or provided.")

    def search_images(self, query: str, num_results: int = 10, site_to_search: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Search for images using Google Custom Search API.
        
        Args:
            query (str): The search query for images.
            num_results (int): Number of image results to return (max 10 per request).
            site_to_search (Optional[str]): Specific site/domain to search images from (e.g., "www.example.com").
                                          If a full URL is provided, only the domain part will be used.
            
        Returns:
            Optional[List[Dict]]: List of image items if found, None if not found or error.
        """
        if not self.api_key or not self.cx: 
            print("Error: API Key or CX is missing for search_images call.") 
            return None
            
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "searchType": "image",
            "num": min(num_results, 10) 
        }

        if site_to_search.lower() != 'null':
            parsed_url = urlparse(site_to_search)
            domain_to_search = parsed_url.netloc or parsed_url.path 
            if not parsed_url.scheme and '/' in domain_to_search:
                 domain_to_search = domain_to_search.split('/')[0]
            if domain_to_search: 
                params["siteSearch"] = domain_to_search
                params["siteSearchFilter"] = "i" 
            else:
                print(f"Warning: Could not extract a valid domain from site_to_search value: {site_to_search}")
        
        response_obj = None
        try:
            response_obj = requests.get(self.base_url, params=params, timeout=10)
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

    def download_images(self, image_download_dir: Path, image_results: List[Dict], event_title_for_filename: str, num_to_download: int, query_context: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Downloads multiple images from a list of image results and saves them locally.
        Filters out URLs that do not appear to be direct image links based on common extensions.

        Args:
            image_download_dir (Path): The directory where images should be saved.
            image_results (List[Dict]): List of image items from search_images.
            event_title_for_filename (str): The title of the event, used for descriptive filenames.
            num_to_download (int): The maximum number of images to attempt to download from the filtered results.
            query_context (str, optional): Context from the original search query for filename.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each containing 'local_path' and 'original_url'
                                  for successfully downloaded images.
        """
        if not image_results:
            print("  Info: No image results provided for download.")
            return []

        image_download_dir.mkdir(parents=True, exist_ok=True)
        downloaded_image_details = []
        attempted_downloads = 0

        COMMON_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

        for i, image_item in enumerate(image_results):
            if attempted_downloads >= num_to_download:
                break 

            image_url = image_item.get('link')
            if not image_url:
                print(f"  Skipping image result {i+1} due to missing URL.")
                continue

            try:
                parsed_url_path = Path(unquote(urlparse(image_url).path))
                if parsed_url_path.suffix.lower() not in COMMON_IMAGE_EXTENSIONS:
                    print(f"  Skipping URL (does not appear to be a direct image link based on extension): {image_url}")
                    continue
            except Exception as e:
                print(f"  Could not parse URL or get extension for {image_url}: {e}. Skipping.")
                continue
            
            attempted_downloads += 1 
            print(f"  Attempting to download image {attempted_downloads}/{num_to_download} (Source item {i+1}): {image_url}")
            filepath_for_error_msg = str(image_download_dir / "unknown_image_file")

            try:
                response = requests.get(image_url, stream=True, timeout=20)
                response.raise_for_status()

                content_type = response.headers.get('content-type')
                extension = parsed_url_path.suffix.lower()

                if content_type:
                    ct_lower = content_type.lower()
                    if 'jpeg' in ct_lower and extension != ".jpg": extension = ".jpg"
                    elif 'png' in ct_lower and extension != ".png": extension = ".png"
                    elif 'gif' in ct_lower and extension != ".gif": extension = ".gif"
                    elif 'webp' in ct_lower and extension != ".webp": extension = ".webp"
                
                filename = f"{event_title_for_filename}_{attempted_downloads}{extension}"
                filepath = image_download_dir / filename

                with open(filepath, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                
                local_path_str = str(filepath.relative_to(Path.cwd()) if filepath.is_absolute() else filepath)
                downloaded_image_details.append({"local_path": local_path_str, "original_url": image_url, "filename": filename})

            except requests.exceptions.Timeout:
                print(f"    Error: Timeout downloading image {image_url}")
            except requests.exceptions.RequestException as e:
                print(f"    Error downloading image {image_url}: {e}")
            except IOError as e:
                print(f"    Error saving image {image_url} to {filepath_for_error_msg}: {e}")
            except Exception as e:
                print(f"    An unexpected error occurred while downloading/saving {image_url}: {e}")
        
        return downloaded_image_details

def load_events_json(json_file_path: str) -> list[dict]:
    """Helper function to load events from a JSON file."""
    try:
        file_path_obj = Path(json_file_path)
        if not file_path_obj.exists():
            print(f"Error: Event JSON file not found at {json_file_path}")
            return []
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            events_data = json.load(f)
        
        if isinstance(events_data, list):
            return events_data
        else:
            print(f"Error: Expected a list or a dictionary (with an 'events' key or a single event) in {json_file_path}, but got {type(events_data)}")
            return []
            
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        return []
    except Exception as e: 
        print(f"An unexpected error occurred while loading {json_file_path}: {e}")
        return []

def main():
    blog_test = "sassymamasg"
    event_file_path = Path(f"events_output/{blog_test}_events.json")
    images_dir = Path(f"events_output/images/{blog_test}")
    images_dir.mkdir(parents=True, exist_ok=True)
    num_images = 10

    try:
        search_api = GoogleCustomSearchAPI()
    except ValueError as e:
        print(f"Error: {e}")
        return

    events = load_events_json(event_file_path)
    image_mapping = {}

    for event in events[::12]:
        title = event.get('title')

        print(f"Searching images for: {title}")
        image_results = search_api.search_images(
            query=title,
            num_results=num_images,
            site_to_search=event.get('url')
        )

        if image_results:
            downloaded_image_details = search_api.download_images(
                image_download_dir=images_dir,
                image_results=image_results,
                event_title_for_filename=title,
                num_to_download=num_images
            )
            
            if downloaded_image_details:
                image_mapping[title] = downloaded_image_details

    with open( "events_output/images/image_mapping.json", 'w', encoding='utf-8') as f:
        json.dump(image_mapping, f, indent=2)

if __name__ == "__main__":
    main()
