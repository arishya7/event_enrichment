#!/usr/bin/env python3
"""
Playwright Test Script for Bypassing Website Blockages
Tests if Playwright can access the Singapore family blogs
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_playwright_access(url, blog_name):
    """Test if Playwright can access a specific URL"""
    
    try:
        from playwright.async_api import async_playwright
        
        print(f"\n🔍 Testing {blog_name} with Playwright...")
        print("=" * 60)
        
        async with async_playwright() as p:
            # Launch browser with stealth options
            browser = await p.chromium.launch(
                headless=False,  # Set to True for production
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-notifications'
                ]
            )
            
            # Create context with stealth settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Asia/Singapore',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Add stealth scripts
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            # Create page
            page = await context.new_page()
            
            # Set extra headers
            await page.set_extra_http_headers({
                'Referer': 'https://www.google.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
            })
            
            print(f"🌐 Navigating to: {url}")
            
            # Navigate with timeout
            try:
                response = await page.goto(url, wait_until='networkidle', timeout=30000)
                
                if response:
                    print(f"✅ Status: {response.status}")
                    print(f"📄 Content Type: {response.headers.get('content-type', 'unknown')}")
                    
                    # Wait a bit for content to load
                    await page.wait_for_timeout(3000)
                    
                    # Get page content
                    content = await page.content()
                    title = await page.title()
                    
                    print(f"📝 Page Title: {title}")
                    print(f"📏 Content Length: {len(content):,} characters")
                    
                    # Check for common blocking indicators
                    if 'cloudflare' in content.lower():
                        print("⚠️  Cloudflare protection detected!")
                    if 'javascript' in content.lower() and 'enable' in content.lower():
                        print("⚠️  JavaScript required detected!")
                    if 'bot' in content.lower() and 'block' in content.lower():
                        print("⚠️  Bot blocking detected!")
                    if 'access denied' in content.lower():
                        print("❌ Access denied detected!")
                    
                    # Try to extract some basic content
                    try:
                        # Look for common content selectors
                        selectors_to_try = [
                            'h1', 'h2', 'h3', 
                            '.title', '.post-title', '.entry-title',
                            'article', '.post-content', '.entry-content',
                            '.content', '.post', 'main'
                        ]
                        
                        extracted_content = {}
                        for selector in selectors_to_try:
                            try:
                                elements = await page.query_selector_all(selector)
                                if elements:
                                    texts = []
                                    for elem in elements[:3]:  # First 3 elements
                                        text = await elem.text_content()
                                        if text and len(text.strip()) > 10:
                                            texts.append(text.strip()[:100] + "...")
                                    if texts:
                                        extracted_content[selector] = texts
                            except Exception as e:
                                continue
                        
                        if extracted_content:
                            print(f"✅ Content extracted from {len(extracted_content)} selectors")
                            for selector, texts in extracted_content.items():
                                print(f"   {selector}: {len(texts)} elements found")
                        else:
                            print("❌ No content could be extracted")
                            
                    except Exception as e:
                        print(f"⚠️  Content extraction failed: {str(e)}")
                    
                    # Save the page content for analysis
                    output_dir = Path("../data/playwright_test")
                    output_dir.mkdir(exist_ok=True)
                    
                    output_file = output_dir / f"{blog_name}_playwright.html"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"💾 Page content saved to: {output_file}")
                    
                    return {
                        'success': True,
                        'status': response.status,
                        'title': title,
                        'content_length': len(content),
                        'content_saved': str(output_file)
                    }
                    
                else:
                    print("❌ No response received")
                    return {'success': False, 'error': 'No response'}
                    
            except Exception as e:
                print(f"❌ Navigation failed: {str(e)}")
                return {'success': False, 'error': str(e)}
            
            finally:
                await browser.close()
                
    except ImportError:
        print("❌ Playwright not installed. Install with: pip install playwright")
        print("   Then run: playwright install chromium")
        return {'success': False, 'error': 'Playwright not installed'}
    except Exception as e:
        print(f"❌ Playwright test failed: {str(e)}")
        return {'success': False, 'error': str(e)}

async def test_all_blogs():
    """Test all the Singapore family blogs with Playwright"""
    
    blogs = {
        "sassymama": "https://www.sassymamasg.com",
        "asianparent": "https://sg.theasianparent.com",
        "bykido": "https://www.bykido.com",
        "honeykidsasia": "https://honeykidsasia.com",
        "honeycombers": "https://thehoneycombers.com/singapore",
        "smartlocal": "https://thesmartlocal.com"
    }
    
    results = {}
    
    print("🧪 Playwright Website Access Test")
    print("=" * 60)
    
    for blog_name, url in blogs.items():
        result = await test_playwright_access(url, blog_name)
        results[blog_name] = result
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Save all results
    output_dir = Path("../data/playwright_test")
    output_dir.mkdir(exist_ok=True)
    
    results_file = output_dir / "playwright_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 All results saved to: {results_file}")
    
    # Summary
    print(f"\n📊 Test Summary:")
    successful = sum(1 for r in results.values() if r.get('success'))
    total = len(results)
    print(f"   Successful: {successful}/{total}")
    
    for blog_name, result in results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"   {status} {blog_name}: {result.get('error', 'Success')}")
    
    return results

def main():
    """Main function"""
    print("🚀 Starting Playwright Tests...")
    
    # Run the async tests
    results = asyncio.run(test_all_blogs())
    
    print(f"\n🎯 Playwright testing complete!")
    print("Check the data/playwright_test/ folder for detailed results")

if __name__ == "__main__":
    main() 