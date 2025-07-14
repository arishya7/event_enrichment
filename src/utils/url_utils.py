import requests
import logging
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# If you want to disable logging for cleaner output during testing, uncomment the next line:
logging.getLogger().setLevel(logging.CRITICAL) 

def validate_url(url: str, timeout: int = 10) -> bool:
    """
    Check if a URL is valid and accessible, handling bot protection and other common blockers.
    
    Args:
        url (str): URL to validate
        timeout (int): Request timeout in seconds (default: 10)
        
    Returns:
        bool: True if URL is accessible, False if 404, blocked, or other error
    """
    if not url or not url.strip():
        return False
        
    ua = UserAgent() # Uncomment if using fake-useragent
    headers = {
        # Using a more generic or potentially randomized User-Agent
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        # 'User-Agent': ua.random, # If using fake-useragent
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Use requests.Session for persistent connection and cookie handling
    with requests.Session() as session:
        session.headers.update(headers) # Apply headers to the session

        # First try HEAD request (faster)
        try:
            response = session.head(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            elif response.status_code in [403, 429, 503]:
                # Fall through to try GET request
                pass
            elif response.status_code == 405: # Method Not Allowed
                pass # Fall through to try GET request
            elif 300 <= response.status_code < 400: # Redirection
                return True
            else:
                return True
                
        except requests.exceptions.RequestException as e_head:
            pass # Continue to GET request

        # If HEAD didn't definitively resolve or was blocked, try GET request
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            
            content_snippet = ""
            try:
                # Read a small portion to check for soft 404s or blocking indicators
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    content_snippet += chunk
                    if len(content_snippet) > 2048:  # Read max 2KB
                        break
            except Exception as e_content:
                pass # If content reading fails, just proceed with status code check
            
            # Close the response to release connection resources
            response.close() 

            # Check status code from GET request
            if response.status_code == 404:
                return False
            elif response.status_code in [403, 429, 503]:
                blocking_indicators = [
                    'cloudflare', 'captcha', 'bot protection', 'access denied',
                    'blocked', 'forbidden', 'rate limit', 'please enable javascript',
                    'robot', 'security check', 'ddos protection'
                ]
                content_lower = content_snippet.lower()
                
                if any(indicator in content_lower for indicator in blocking_indicators):
                    return True  # URL exists but is protected - consider it valid
                else:
                    return False
            elif 200 <= response.status_code < 300: # Successful responses (2xx)
                soft_404_indicators = [
                    'page not found', 'error 404', 'not found',
                    'this page does not exist', 'page unavailable', 'resource not found'
                ]
                content_lower = content_snippet.lower()
                
                if any(indicator in content_lower for indicator in soft_404_indicators):
                    return False  # Soft 404
                else:
                    return True  # Genuine 200 response
            elif 300 <= response.status_code < 400: # Redirection (3xx)
                return True
            else:
                # For other status codes (e.g., server errors 5xx)
                # Decision: Treat 5xx as "accessible but experiencing server issues".
                return True
                
        except requests.exceptions.Timeout:
            return True  # Timeout doesn't mean URL is invalid
        except requests.exceptions.TooManyRedirects:
            return False # Infinite redirect loop or excessive redirects
        except requests.exceptions.ConnectionError as e:
            return False
        except requests.exceptions.RequestException as e_get:
            return False

# --- Example Usage (for testing) ---
if __name__ == "__main__":
    print("\n--- Testing URLs ---")

    test_urls = {
        "Valid Google": "https://www.google.com",  # Should be True
        "Non-existent page": "https://www.google.com/nonexistentpage12345XYZ", # Should be False (404)
        "HTTP 404 Status": "https://httpstat.us/404", # Should be False
        "HTTP 403 Forbidden": "https://httpstat.us/403", # Should be True (blocked but exists)
        "HTTP 500 Server Error": "https://httpstat.us/500", # Should be True (server error, but accessible endpoint)
        "Cloudflare Protected (often)": "https://www.cloudflare.com/", # Should be True (might show warning, but accessible)
        "Example.com": "https://example.com", # Should be True
        "Empty string": "", # Should be False
        "Whitespace string": "   ", # Should be False
        "Invalid format": "htp://inva lid.com", # Should be False (ConnectionError)
        "Slow site (example)": "https://www.nasa.gov/", # Might timeout sometimes depending on network (True)
        "Soft 404 (simulated)": "https://scontent.cdninstagram.com/o7/v/t0f.nonexistenturl", # Often returns 200 with 'page not found' text. This is a common pattern for soft 404s. Will return False.
        "Redirect Chain": "http://httpbin.org/redirect/5", # Should be True (follows redirects)
        "Too Many Redirects": "http://httpbin.org/redirect/21", # Should be False (TooManyRedirects)
        # You might need to find a real-world example that reliably triggers a JS challenge.
        # "JS Challenge (will likely fail gracefully)": "https://www.nike.com/",
    }

    for name, url in test_urls.items():
        is_valid = validate_url(url, timeout=5) # Reduced timeout for faster testing
        print(f"Result for '{name}': {is_valid}")
        print("-" * 30)