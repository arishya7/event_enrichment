import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

IMG_ATTRS = ["src","data-src","data-original","data-lazy","data-img","data-bg","data-background"]
# Only allow these image formats: jpg, jpeg, png, webp
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")

def score_image_relevance(img_url: str, element=None, page_title="") -> float:
    """Score image by how likely it is to be main content (0-100)."""
    score = 0.0
    url_lower = img_url.lower()
    
    # Meta tags are usually the main image (handled separately)
    # +50 for large/hero/main keywords in URL
    if any(kw in url_lower for kw in ['hero', 'main', 'banner', 'feature', 'primary', 'large', 'big']):
        score += 50
    
    # +30 for dimension hints (800x600, 1200x800, etc.)
    dim_match = re.search(r'(\d{3,4})x(\d{3,4})', url_lower)
    if dim_match:
        w, h = int(dim_match.group(1)), int(dim_match.group(2))
        if w >= 800 and h >= 600:  # Large images likely main content
            score += 30
    
    # +20 for being in main content paths
    if any(path in url_lower for path in ['/content/', '/images/', '/media/', '/uploads/', '/assets/']):
        score += 20
    
    # -30 for sidebar/footer/header/thumbnail patterns
    if any(bad in url_lower for bad in ['sidebar', 'footer', 'header', 'nav', 'thumbnail', 'thumb/', 'mini', 'small-']):
        score -= 30
    
    # +15 if element is in main/article/content containers
    if element:
        parent_classes = ' '.join([
            str(element.parent.get('class', [])),
            str(element.parent.parent.get('class', [])) if element.parent.parent else ''
        ]).lower()
        if any(container in parent_classes for container in ['main', 'content', 'article', 'post', 'hero', 'feature']):
            score += 15
        # Penalize sidebar/footer containers
        if any(bad_container in parent_classes for bad_container in ['sidebar', 'footer', 'header', 'nav', 'widget']):
            score -= 20
    
    # +10 for relevance to page title/keywords
    if page_title:
        title_words = set(re.findall(r'\w+', page_title.lower()))
        url_words = set(re.findall(r'\w+', url_lower))
        overlap = len(title_words & url_words)
        if overlap > 0:
            score += min(overlap * 5, 10)
    
    return max(0, min(100, score))

def filter_image(url):
    if not url: return False
    u = url.lower().strip()
    
    # Skip empty or invalid URLs
    if not u or u == 'none' or u == 'null': return False
    
    # Skip data URIs (data:image/...)
    if u.startswith('data:'): return False
    
    # Skip non-HTTP URLs
    if not (u.startswith('http://') or u.startswith('https://')):
        # Allow relative URLs that will be resolved later
        if not u.startswith('/') and not u.startswith('./'): return False
    
    # Skip known non-content patterns
    skip = ["logo","icon","sprite","avatar","pixel","loader","placeholder","tracking","badge","button","arrow","thumb","favicon"]
    if any(s in u for s in skip): return False
    
    # Reject unsupported formats explicitly (SVG, GIF, BMP, etc.)
    unsupported_exts = ('.svg', '.gif', '.bmp', '.ico', '.tiff', '.tif', '.eps', '.raw', '.cr2', '.nef', '.orf', '.sr2')
    if u.endswith(unsupported_exts): return False
    
    # Must be an allowed image extension or contain image-related keywords (but will validate format later)
    if not u.endswith(IMG_EXTS) and not re.search(r"image|img|photo", u): return False
    
    return True

def extract_static_html_images(url, max_images=3):
    """Fast HTML parse for websites with visible <img> tags"""
    try:
        html = requests.get(url, headers={"User-Agent":"Mozilla"}, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        
        # Get page title for relevance scoring
        page_title = ""
        if soup.title:
            page_title = soup.title.string or ""
        
        # Priority 1: Meta tags (og:image, twitter:image) - highest relevance
        meta_images = []
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '') or meta.get('name', '')
            if prop.lower() in ['og:image', 'twitter:image', 'og:image:url']:
                if meta.get('content'):
                    img_url = urljoin(url, meta['content'])
                    if filter_image(img_url):
                        meta_images.append((img_url, 100.0))  # Highest score
        
        # Priority 2: Standard <img> & lazy attributes with scoring
        scored_imgs = []
        for img in soup.find_all("img"):
            for attr in IMG_ATTRS:
                if img.get(attr):
                    img_url = urljoin(url, img[attr])
                    if filter_image(img_url):
                        score = score_image_relevance(img_url, img, page_title)
                        scored_imgs.append((img_url, score))

        # Priority 3: background-image inline styles
        for el in soup.find_all(style=True):
            m = re.findall(r'background-image:\s*url\((.*?)\)', el.get('style', ''))
            for u in m:
                img_url = urljoin(url, u.strip(" \"'"))
                if filter_image(img_url):
                    score = score_image_relevance(img_url, el, page_title)
                    scored_imgs.append((img_url, score))

        # Combine and sort by score (highest first)
        all_imgs = meta_images + scored_imgs
        # Deduplicate by URL, keeping highest score
        seen = {}
        for url, score in all_imgs:
            if url not in seen or score > seen[url]:
                seen[url] = score
        
        # Sort by score and return top N (with final validation)
        sorted_imgs = sorted(seen.items(), key=lambda x: x[1], reverse=True)
        valid_urls = []
        for img_url, score in sorted_imgs[:max_images]:
            # Final validation: ensure URL is absolute and valid
            if not img_url: continue
            img_url_lower = img_url.lower().strip()
            # Must be valid HTTP/HTTPS URL
            if img_url_lower.startswith('http://') or img_url_lower.startswith('https://'):
                # Remove URL fragments (#anchor) but keep query params (?key=val)
                clean_url = img_url.split('#')[0]
                if clean_url and clean_url not in valid_urls:
                    valid_urls.append(clean_url)
        return valid_urls[:max_images]
    except Exception as e:
        print(f"Error in static extraction: {e}")
        return []

def extract_dynamic_images(url, max_images=2):
    """JS-rendered DOM + network capture"""
    scored_imgs = {}
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Network listener (most reliable) - score network images
            def on_response(response):
                if response.request.resource_type == "image":
                    img_url = response.url
                    if filter_image(img_url):
                        score = score_image_relevance(img_url, None, "")
                        if img_url not in scored_imgs or score > scored_imgs[img_url]:
                            scored_imgs[img_url] = score

            page.on("response", on_response)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                page_title = ""
                if soup.title:
                    page_title = soup.title.string or ""

                # DOM extraction with scoring
                for img in soup.find_all("img"):
                    for attr in IMG_ATTRS:
                        if img.get(attr):
                            img_url = urljoin(url, img[attr])
                            if filter_image(img_url):
                                score = score_image_relevance(img_url, img, page_title)
                                if img_url not in scored_imgs or score > scored_imgs[img_url]:
                                    scored_imgs[img_url] = score

                for el in soup.find_all(style=True):
                    m = re.findall(r'background-image:\s*url\((.*?)\)', el.get('style', ''))
                    for u in m:
                        img_url = urljoin(url, u.strip(" \"'"))
                        if filter_image(img_url):
                            score = score_image_relevance(img_url, el, page_title)
                            if img_url not in scored_imgs or score > scored_imgs[img_url]:
                                scored_imgs[img_url] = score
            except Exception as goto_error:
                print(f"Error navigating to {url}: {goto_error}")
                # Return empty list if navigation fails
                if browser:
                    try:
                        browser.close()
                    except:
                        pass
                return []
            
            if browser:
                browser.close()
    except Exception as e:
        print(f"Error in dynamic extraction: {e}")
        if browser:
            try:
                browser.close()
            except:
                pass
        return []

    # Sort by score and return top N
    sorted_imgs = sorted(scored_imgs.items(), key=lambda x: x[1], reverse=True)
    valid_urls = []
    for img_url, score in sorted_imgs[:max_images]:
        # Final validation: ensure URL is absolute and valid
        if not img_url: continue
        img_url_lower = img_url.lower().strip()
        # Must be valid HTTP/HTTPS URL
        if img_url_lower.startswith('http://') or img_url_lower.startswith('https://'):
            # Remove URL fragments (#anchor) but keep query params (?key=val)
            clean_url = img_url.split('#')[0]
            if clean_url and clean_url not in valid_urls:
                valid_urls.append(clean_url)
    return valid_urls[:max_images]

def extract_images(url, max_images=3):
    """
    Extract the most relevant images from a webpage.
    Returns top 1-2 images related to main content, not sidebars/footers.
    """
    print(f"🔍 Scanning for top {max_images} relevant images...")
    static_imgs = extract_static_html_images(url, max_images=max_images)
    if static_imgs:
        print(f"Found {len(static_imgs)} relevant images (static HTML)")
        return static_imgs

    print("No relevant images in static HTML — trying dynamic mode...")
    dynamic_imgs = extract_dynamic_images(url, max_images=max_images)
    print(f"Found {len(dynamic_imgs)} relevant images (dynamic)")
    return dynamic_imgs

if __name__ == "__main__":
    url = "https://eatbook.sg/sing-hon-loong-bakery/"
    imgs = extract_images(url)
    for i, img in enumerate(imgs, 1):
        print(f"{i}. {img}")
