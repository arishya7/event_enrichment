"""
Google Custom Search API Service

This module provides functionality for searching the web using Google's Custom Search API.
It includes functions for finding valid URLs for events, searching for images, and
validating URLs to ensure they're accessible.

The service is specifically configured for event and activity searches, with built-in
exclusions for certain sites and support for both general and site-specific searches.

Features:
- Event URL discovery using event titles and organizer information
- Image search with site-specific and general search capabilities
- URL validation to check for 404 errors
- Automatic exclusion of unwanted sites
- Safe search filtering for image searches
- Timeout handling and error recovery

Dependencies:
- requests: HTTP client for API calls
- dotenv: Environment variable loading
- urllib.parse: URL parsing utilities

Configuration:
- Requires GOOGLE_API_KEY environment variable
- Requires cx (Custom Search Engine ID) environment variable
- Uses config module for API credentials

Example Usage:
    from src.services import search_valid_url, search_images, validate_url
    
    # Find event URL
    url = search_valid_url("Kids Art Workshop", "Art Studio")
    
    # Search for images
    images = search_images("kids activities singapore", num_results=5)
    
    # Validate URL
    valid_url = validate_url("https://example.com/event")
"""

import requests
from typing import Optional, List
from dotenv import load_dotenv
import os
import requests

from urllib.parse import urlparse
from src.utils.config import config
load_dotenv()

# Global constants for search configuration
BASE_URL = "https://www.googleapis.com/customsearch/v1"
# Sites to exclude from search results to avoid low-quality content
EXCLUDE_SITES = "lookaside OR sassymamasg OR honeykidsasia OR thesmartlocal OR theasianparent OR bykido OR skoopsg OR littledayout OR twolittlefeet"

def search_valid_url(event_title: str, organiser: str = "") -> Optional[str]:
    """
    Search for a valid URL for an event using Google Custom Search API.
    
    This function searches for event-specific URLs by combining the event title
    with organizer information. It uses the Google Custom Search API to find
    relevant web pages and returns the first valid URL found.
    
    The search is optimized for event discovery by:
    - Combining event title with organizer name for better results
    - Excluding known low-quality sites
    - Requesting multiple results to increase success rate
    - Using timeout handling for reliability
    
    Args:
        event_title (str): Title of the event to search for
        organiser (str): Event organiser name (optional, improves search accuracy)
        
    Returns:
        Optional[str]: First valid URL found, or None if no valid URL found
        
    Raises:
        requests.RequestException: If the API request fails
        KeyError: If the API response doesn't contain expected data
        
    Example:
        url = search_valid_url("Summer Art Camp", "Creative Kids Studio")
        # Returns: "https://creativekidsstudio.com/summer-art-camp"
    """
    # Use config values (loaded from .env) - these are the source of truth
    api_key = config.google_api_key
    cx = config.cx

    if not api_key or not cx:
        print("Error: API Key or CX is missing for search_valid_url call.")
        print(f"  API Key present: {bool(api_key)}")
        print(f"  CX present: {bool(cx)}")
        return None

    # Build search query with available information
    # Combine event title and organizer for better search results
    query_parts = [event_title]
    if organiser:
        query_parts.append(organiser)
    
    search_query = " ".join(query_parts)
    
    try:
        params = {
            "key": api_key, 
            "cx": cx, 
            "q": search_query,
            "num": 10,  # Get more results to increase chances of finding valid URL
            "excludeTerms": EXCLUDE_SITES
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['items'][0]['link']
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"│ │ │ [custom_search.search_valid_url] 403 Forbidden - API key issue:")
            print(f"│ │ │   - Check if Custom Search API is enabled in Google Cloud Console")
            print(f"│ │ │   - Verify API key has Custom Search API permissions")
            print(f"│ │ │   - Check if daily quota (100 free queries) is exceeded")
            print(f"│ │ │   - Ensure you're using a Google Cloud API key (not Gemini API key)")
        else:
            print(f"│ │ │ [custom_search.search_valid_url] HTTP Error {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"│ │ │ [custom_search.search_valid_url] Search failed: {e}")
        return None

def search_images(query: str, num_results: int = 10, site_to_search: Optional[str] = None, safe_search: bool = True) -> Optional[List[str]]:
    """
    Search for images using Google Custom Search API.
    
    This function performs image searches with support for both general web searches
    and site-specific searches. It can search within a specific website or across
    the entire web, with configurable result counts and safe search filtering.
    
    The search strategy:
    1. If a specific site is provided, search within that site first
    2. Perform a general web search for additional results
    3. Combine and deduplicate results
    4. Apply safe search filtering if enabled
    
    Args:
        query (str): Search query string for finding images
        num_results (int): Number of results to return (default: 10)
        site_to_search (Optional[str]): Specific site to search within (e.g., "example.com")
        safe_search (bool): Enable safe search filtering (default: True)
        
    Returns:
        Optional[List[str]]: List of image URLs or None if search fails
        
    Example:
        # Search for images on a specific site
        images = search_images("kids activities", site_to_search="example.com")
        
        # General web search
        images = search_images("singapore events", num_results=5)
    """
    # Use config values (loaded from .env)
    api_key = config.google_api_key
    cx = config.cx

    if not api_key or not cx:
        print("Error: API Key or CX is missing for search_images call.")
        print(f"  API Key present: {bool(api_key)}")
        print(f"  CX present: {bool(cx)}")
        return None

    found_urls = set()  # Use set to avoid duplicates
    num_site_results = num_results // 2
    num_general_results = num_results - num_site_results

    # First, search within the specific site if provided
    if site_to_search and site_to_search.lower() != 'null' and num_site_results > 0:
        try:
            netloc = urlparse(site_to_search).netloc
            if netloc:
                params = {
                    "key": api_key, 
                    "cx": cx, 
                    "q": query,
                    "searchType": "image", 
                    "num": num_site_results,
                    "siteSearch": netloc, 
                    "siteSearchFilter": "i",  # 'i' means search only within the site
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

    # Then, perform a general web search for additional results
    if num_general_results > 0:
        try:
            params = {
                "key": api_key, 
                "cx": cx, 
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

def validate_url(url: str) -> Optional[str]:
    """
    Check if the given URL does not return a 404 error.
    
    This function performs a HEAD request to check if a URL is accessible.
    If the server doesn't support HEAD requests, it falls back to a GET request.
    URLs that return 404 are considered invalid, while other errors (timeout,
    connection issues) are treated as potentially valid.
    
    Args:
        url (str): URL to validate
        
    Returns:
        Optional[str]: The URL if valid (including unreachable), or None if 404
        
    Example:
        valid_url = validate_url("https://example.com/event")
        # Returns: "https://example.com/event" if accessible, None if 404
    """
    try:
        # Try HEAD request first (more efficient)
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code == 405:  # Method not allowed
            # Fall back to GET request
            response = requests.get(url, allow_redirects=True, timeout=5)
        if response.status_code == 404:
            return None
        return url
    except requests.RequestException:
        # Treat unreachable URLs as potentially valid (return the URL)
        # This is because temporary network issues shouldn't invalidate a URL
        return url

def main():
    """
    Test function for direct script execution.
    
    Provides an interactive testing interface for the search functions.
    Useful for debugging and testing search functionality independently.
    """
    print("--- Running custom_search.py directly for testing ---")
    search_query = input("Enter a search query: ")
    site_to_search = input("Enter a site to search: ")
    print(search_images(search_query, num_results=10, site_to_search=site_to_search))

if __name__ == "__main__":
    main()
