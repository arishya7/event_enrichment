"""
Improved Email Scraper - Event/Brand Contact Finder
Finds organizer or official contact emails efficiently.
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT = 8
CRAWL_DEPTH = 1  # Reduced from 2 - only follow 1 level of links
RATE_LIMIT = 0.3  # Reduced from 1.0 - faster scraping
MAX_LINKS_PER_PAGE = 3  # Limit how many contact/about links to follow

EMAIL_REGEX = re.compile(
    r'[\w\.-]+@[\w\.-]+\.\w+|[\w\.-]+\s?\[at\]\s?[\w\.-]+\s?\[dot\]\s?\w+',
    re.I
)

RELEVANT_KEYWORDS = [
    "contact", "about", "team", "reach", "support", "event", "organizer",
    "customer", "enquiry", "feedback", "marketing", "info"
]

PREFERRED_HANDLES = [
    "info", "event", "marketing", "sales", "support", "contact",
    "hello", "feedback", "enquiry", "admin"
]


def fetch_html(url: str, use_js=False) -> Optional[str]:
    """Fetch page HTML, optionally with Playwright for JS-heavy sites."""
    try:
        if use_js and PLAYWRIGHT_AVAILABLE:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                html = page.content()
                browser.close()
                return html
        else:
            res = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if "text/html" in res.headers.get("Content-Type", ""):
                return res.text
    except Exception:
        return None
    return None


def extract_emails(html: str) -> Set[str]:
    """Extract raw and obfuscated emails from HTML."""
    found = set()
    for match in EMAIL_REGEX.findall(html):
        clean = match.replace("[at]", "@").replace("[dot]", ".").replace(" ", "")
        found.add(clean.lower())
    return found


def get_relevant_links(base_url: str, html: str) -> List[str]:
    """Collect likely contact or about page links within same domain."""
    soup = BeautifulSoup(html, "html.parser")
    base = urlparse(base_url).netloc
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if any(k in href.lower() for k in RELEVANT_KEYWORDS):
            full = urljoin(base_url, href)
            if urlparse(full).netloc == base:
                links.add(full)
    return list(links)


def filter_priority_emails(emails: Set[str]) -> List[str]:
    """Rank/filter emails based on priority patterns."""
    priority = [e for e in emails if any(h in e for h in PREFERRED_HANDLES)]
    domain_emails = [e for e in emails if not any(x in e for x in ["gmail", "yahoo", "hotmail", "outlook"])]
    if priority:
        return priority
    if domain_emails:
        return domain_emails
    return list(emails)


def scrape_event_emails(start_url: str, use_js=False) -> List[str]:
    """Main entry — crawl contact pages, collect prioritized emails.
    
    Optimized for speed:
    - Try simple request first, only use JS if needed
    - Stop early if good emails found on first page
    - Limit number of links followed
    """
    visited = set()
    found_emails = set()
    
    # First, try simple request (fast)
    html = fetch_html(start_url, use_js=False)
    if html:
        visited.add(start_url)
        found_emails |= extract_emails(html)
        
        # If we found good emails on first page, return early
        priority_emails = filter_priority_emails(found_emails)
        if priority_emails:
            return priority_emails
        
        # Get contact/about links to check
        contact_links = get_relevant_links(start_url, html)[:MAX_LINKS_PER_PAGE]
        
        # Check contact pages
        for link in contact_links:
            if link in visited:
                continue
            visited.add(link)
            
            link_html = fetch_html(link, use_js=False)
            if link_html:
                found_emails |= extract_emails(link_html)
            
            time.sleep(RATE_LIMIT)
            
            # Early exit if we found good emails
            if found_emails:
                priority = filter_priority_emails(found_emails)
                if priority:
                    return priority
    
    # If still no emails and JS is requested, try with Playwright (slower)
    if not found_emails and use_js and PLAYWRIGHT_AVAILABLE:
        html = fetch_html(start_url, use_js=True)
        if html:
            found_emails |= extract_emails(html)
    
    return filter_priority_emails(found_emails)


def extract_company_emails_from_event(event_page_url: str, use_playwright: bool = True, mx_validate: bool = False) -> List[str]:
    """Compatibility wrapper: extract organizer/company emails starting from an event URL.
    Uses scrape_event_emails under the hood. mx_validate is ignored here.
    """
    return scrape_event_emails(event_page_url, use_js=use_playwright)


if __name__ == "__main__":
    test_url = "https://playpoint.asia/"
    emails = scrape_event_emails(test_url, use_js=True)
    print("Organizer Emails Found:", emails)