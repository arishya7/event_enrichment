import requests
from typing import Optional, List
from dotenv import load_dotenv
import os
from urllib.parse import urlparse
from src.utils.config import config
load_dotenv()

# Global constants
BASE_URL = "https://www.googleapis.com/customsearch/v1"
EXCLUDE_SITES = "lookaside OR sassymamasg OR honeykidsasia OR thesmartlocal OR theasianparent OR bykido OR skoopsg"



def search_valid_url(event_title: str, organiser: str = "", venue_name: str = "") -> Optional[str]:
    """
    Search for a valid URL for an event using Google Custom Search API.
    
    Args:
        event_title (str): Title of the event
        organiser (str): Event organiser name (optional)
        venue_name (str): Venue name (optional)
        
    Returns:
        Optional[str]: First valid URL found, or None if no valid URL found
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("cx")

    if not api_key or not cx:
        print("Error: API Key or CX is missing for search_valid_url call.")
        return None

    # Build search query with available information
    query_parts = [event_title]
    if organiser:
        query_parts.append(organiser)
    if venue_name:
        query_parts.append(venue_name)
    
    search_query = " ".join(query_parts)
    
    try:
        params = {
            "key": config.google_api_key, 
            "cx": config.cx, 
            "q": search_query,
            "num": 10,  # Get more results to increase chances of finding valid URL
            "excludeTerms": EXCLUDE_SITES
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['items'][0]['link']
        
    except Exception as e:
        print(f"│ │ │ [custom_search.search_valid_url] Search failed: {e}")
        return None

def search_images(query: str, num_results: int = 10, site_to_search: Optional[str] = None, safe_search: bool = True) -> Optional[List[str]]:
    """
    Search for images using Google Custom Search API.
    
    Args:
        query (str): Search query string
        num_results (int): Number of results to return (default: 10)
        site_to_search (Optional[str]): Specific site to search within
        safe_search (bool): Enable safe search filtering (default: True)
        
    Returns:
        Optional[List[str]]: List of image URLs or None if search fails
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("cx")

    if not api_key or not cx:
        print("Error: API Key or CX is missing for search_images call.")
        return None

    found_urls = set()
    num_site_results = num_results // 2
    num_general_results = num_results - num_site_results

    if site_to_search and site_to_search.lower() != 'null' and num_site_results > 0:
        try:
            netloc = urlparse(site_to_search).netloc
            if netloc:
                params = {
                    "key": config.google_api_key, 
                    "cx": config.cx, 
                    "q": query,
                    "searchType": "image", 
                    "num": num_site_results,
                    "siteSearch": netloc, 
                    "siteSearchFilter": "i",
                    "excludeTerms": EXCLUDE_SITES,
                    "safe": "active" if safe_search else "off"
                }
                response = requests.get(BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                for item in data.get("items", []):
                    found_urls.add(item['link'])
        except Exception as e:
            print(f"Site-restricted search failed: {e}")

    if num_general_results > 0:
        try:
            params = {
                "key": config.google_api_key, 
                "cx": config.cx, 
                "q": query,
                "searchType": "image", 
                "num": num_general_results,
                "excludeTerms": EXCLUDE_SITES,
                "safe": "active" if safe_search else "off"
            }
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            for item in data.get("items", []):
                found_urls.add(item['link'])
        except Exception as e:
            print(f"Broad image search failed: {e}")

    if not found_urls:
        print(f"│ │ │ [custom_search.search_images] No images found from any source. Query: {query}")
        return None
    
    return list(found_urls)

def main():
    """Test function for direct script execution."""
    print("--- Running custom_search.py directly for testing ---")
    search_query = input("Enter a search query: ")
    site_to_search = input("Enter a site to search: ")
    print(search_images(search_query, num_results=10, site_to_search=site_to_search))

if __name__ == "__main__":
    main()
