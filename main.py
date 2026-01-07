import time
import sys
import argparse
import json
from pathlib import Path


def load_category_pages():
    """Load category pages from config."""
    config_path = Path("config/config.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('category_pages', {})
    return {}


def show_menu():
    """Display the main menu and get user choice."""
    print("\nSelect scraping mode:\n")
    print("  1. RSS Feed Scrape (Normal Flow)")
    print("     → Scrape latest articles from configured RSS feeds")
    print()
    print("  2. Category Page Scrape")
    print("     → Scrape articles from a predefined category page")
    print()
    print("  3. Single Article Scrape")
    print("     → Scrape events from a specific article URL you provide")
    print()
    print("  4. Exit")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)


def run_rss_scrape(args):
    """Run the normal RSS feed scraping flow."""
    # Import here to avoid loading heavy dependencies until needed
    from src.core.run import Run
    
    timestamp = args.timestamp or time.strftime("%Y%m%d_%H%M%S")
    max_articles = args.max_articles if args.max_articles and args.max_articles > 0 else None
    
    run = Run(timestamp=timestamp, blog_name=args.blog, max_articles=max_articles)
    
    if args.blog:
        print(f"📝 Processing single blog: {args.blog}")
    else:
        print(f"📝 Processing all blogs")
    
    if max_articles:
        print(f"📰 Limiting to first {max_articles} articles per blog")
    
    run.start()


def run_category_scrape(args):
    """Run category page scraping with predefined category links."""
    from src.scrapers.category_scraper import CategoryScraper
    from src.core.run import Run
    
    print("\n" + "="*60)
    print("📂 CATEGORY PAGE SCRAPE")
    print("="*60)
    
    # Load category pages from config
    category_pages = load_category_pages()
    
    if not category_pages:
        print("\n❌ No category pages configured in config/config.json")
        return
    
    # Show available blogs
    print("\nSelect a blog:\n")
    blogs = list(category_pages.keys())
    for i, blog in enumerate(blogs, 1):
        print(f"  {i}. {blog}")
    print()
    
    # Get blog selection
    while True:
        try:
            blog_choice = input(f"Enter blog number (1-{len(blogs)}): ").strip()
            blog_idx = int(blog_choice) - 1
            if 0 <= blog_idx < len(blogs):
                selected_blog = blogs[blog_idx]
                break
            print(f"Invalid choice. Please enter 1-{len(blogs)}.")
        except ValueError:
            print(f"Invalid input. Please enter a number 1-{len(blogs)}.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return
    
    # Special handling for honeykidsasia - category scraping doesn't work, ask for URL instead
    if selected_blog.lower() == 'honeykidsasia':
        print(f"\n⚠️ Category page scraping is not supported for {selected_blog}.")
        print("   Please enter a specific article URL instead.\n")
        
        # Show available category links from config so they can browse and find articles
        if selected_blog in category_pages:
            pages = category_pages[selected_blog]
            print("📂 Available category pages (browse these to find article URLs):\n")
            for i, page in enumerate(pages, 1):
                print(f"  {i}. {page['name']}")
                print(f"     {page['url']}")
            print()
        
        print("Example article URLs:")
        print("  • https://honeykidsasia.com/things-to-do-with-kids-during-school-holidays-singapore/")
        print("  • https://honeykidsasia.com/things-to-do-with-kids/indoor-playgrounds-attractions/")
        print()
        
        url = input("Enter article URL: ").strip()
        if not url:
            print("No URL provided. Returning to menu.")
            return
        
        # Validate URL
        if not url.startswith('http'):
            print("❌ Invalid URL. Must start with http:// or https://")
            return
        
        selected_page = {'name': 'Custom Article', 'url': url}
        print(f"\n✅ Selected URL: {url[:70]}...")
    else:
        # Show category pages for selected blog
        pages = category_pages[selected_blog]
        print(f"\n📂 {selected_blog.upper()} - Select a category:\n")
        for i, page in enumerate(pages, 1):
            print(f"  {i}. {page['name']}")
            print(f"     {page['url'][:60]}...")
        print()
        
        # Get category selection
        while True:
            try:
                cat_choice = input(f"Enter category number (1-{len(pages)}): ").strip()
                cat_idx = int(cat_choice) - 1
                if 0 <= cat_idx < len(pages):
                    selected_page = pages[cat_idx]
                    break
                print(f"Invalid choice. Please enter 1-{len(pages)}.")
            except ValueError:
                print(f"Invalid input. Please enter a number 1-{len(pages)}.")
            except KeyboardInterrupt:
                print("\nCancelled.")
                return
        
        url = selected_page['url']
        print(f"\n✅ Selected: {selected_page['name']}")
        print(f"   URL: {url}")
    
    # Use max_articles from args if provided, otherwise ask
    if args.max_articles:
        max_articles = args.max_articles
        print(f"   Max articles: {max_articles}")
    else:
        try:
            max_articles_input = input("\nMax articles to scrape (default: 5): ").strip()
            max_articles = int(max_articles_input) if max_articles_input else 5
        except ValueError:
            max_articles = 5
    
    # Step 1: Extract events using CategoryScraper
    scraper = CategoryScraper(url, max_articles=max_articles)
    raw_events = scraper.scrape()
    
    if not raw_events:
        print("\n❌ No events extracted")
        return
    
    print(f"\n✅ Extracted {len(raw_events)} raw events")
    
    # Step 2: Process through full pipeline
    timestamp = args.timestamp or time.strftime("%Y%m%d_%H%M%S")
    run = Run(timestamp=timestamp, blog_name=None, max_articles=None)
    
    # Process the raw events through the pipeline
    source_name = f"{selected_blog}_{selected_page['name'].lower().replace(' ', '_')}"
    processed_events = run.process_raw_events(raw_events, source_name=source_name)
    
    if processed_events:
        print(f"\n✅ {len(processed_events)} events after full pipeline processing")
    else:
        print("\n❌ No events passed the pipeline filters")


def run_single_article_scrape(args):
    """Run single article scraping - user provides the URL."""
    from src.scrapers.category_scraper import CategoryScraper
    from src.core.run import Run
    
    print("\n" + "="*60)
    print("📄 SINGLE ARTICLE SCRAPE")
    print("="*60)
    
    print("\nPaste an article URL that contains multiple events/venues.")
    print("Examples:")
    print("  • https://honeykidsasia.com/things-to-do-with-kids-during-school-holidays-singapore/")
    print("  • https://www.sassymamasg.com/best-new-restaurants-singapore/")
    print("  • https://www.bykido.com/blogs/guides-and-reviews-singapore/indoor-playgrounds-guide")
    print()
    
    url = input("Enter article URL: ").strip()
    if not url:
        print("No URL provided. Returning to menu.")
        return
    
    # Validate URL
    if not url.startswith('http'):
        print("❌ Invalid URL. Must start with http:// or https://")
        return
    
    # Step 1: Extract events using CategoryScraper
    print(f"\n🔗 Scraping: {url[:60]}...")
    scraper = CategoryScraper(url, max_articles=1, single_article_mode=True)
    raw_events = scraper.scrape_single_article(url)
    
    if not raw_events:
        print("\n❌ No events extracted from article")
        return
    
    print(f"\n✅ Extracted {len(raw_events)} events from article")
    
    # Show preview
    print("\nEvents found:")
    for i, event in enumerate(raw_events[:10], 1):
        title = event.get('title', 'Untitled')[:50]
        venue = event.get('venue_name', 'Unknown')
        print(f"  {i}. {title} @ {venue}")
    
    if len(raw_events) > 10:
        print(f"  ... and {len(raw_events) - 10} more")
    
    # Ask if user wants to process through full pipeline
    print()
    process = input("Process through full pipeline (dedup, filter, images, S3)? (y/n): ").strip().lower()
    
    if process == 'y':
        # Step 2: Process through full pipeline
        timestamp = args.timestamp or time.strftime("%Y%m%d_%H%M%S")
        run = Run(timestamp=timestamp, blog_name=None, max_articles=None)
        
        # Determine source name from URL
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
        
        # Process the raw events through the pipeline
        processed_events = run.process_raw_events(raw_events, source_name=f"{domain}_article")
        
        if processed_events:
            print(f"\n✅ {len(processed_events)} events after full pipeline processing")
        else:
            print("\n❌ No events passed the pipeline filters")
    else:
        # Just save raw events
        save = input("\nSave raw events to JSON instead? (y/n): ").strip().lower()
        if save == 'y':
            scraper.save_events(raw_events)


def main():
    parser = argparse.ArgumentParser(description='Run web scraping and event extraction pipeline')
    parser.add_argument(
        '--blog',
        type=str,
        default=None,
        help='Process only a specific blog (e.g., --blog thesmartlocal). If not specified, processes all blogs.'
    )
    parser.add_argument(
        '--timestamp',
        type=str,
        default=None,
        help='Custom timestamp for the run (default: auto-generated)'
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=None,
        help='Limit the number of articles processed per blog (e.g., --max-articles 10)'
    )
    parser.add_argument(
        '--mode',
        type=int,
        choices=[1, 2, 3],
        default=None,
        help='Scraping mode: 1=RSS, 2=Category, 3=Single Article (skips menu)'
    )
    parser.add_argument(
        '--url',
        type=str,
        default=None,
        help='URL for single article scraping (used with --mode 3)'
    )
    
    args = parser.parse_args()
    
    # If mode is specified via command line, run directly without menu
    if args.mode:
        if args.mode == 1:
            run_rss_scrape(args)
        elif args.mode == 2:
            # Category mode - still needs interactive selection
            run_category_scrape(args)
        elif args.mode == 3:
            if args.url:
                from src.scrapers.category_scraper import CategoryScraper
                from src.core.run import Run
                from urllib.parse import urlparse
                
                scraper = CategoryScraper(args.url, max_articles=1, single_article_mode=True)
                raw_events = scraper.scrape_single_article(args.url)
                
                if raw_events:
                    timestamp = args.timestamp or time.strftime("%Y%m%d_%H%M%S")
                    run = Run(timestamp=timestamp, blog_name=None, max_articles=None)
                    domain = urlparse(args.url).netloc.replace('www.', '').split('.')[0]
                    run.process_raw_events(raw_events, source_name=f"{domain}_article")
            else:
                print("Error: --url required for single article mode")
        return
    
    # Show header and current settings
    print("\n" + "="*60)
    print("🌐 WEB SCRAPING - EVENT EXTRACTION PIPELINE")
    print("="*60)
    
    if args.blog or args.max_articles:
        print("\n📋 Current settings:")
        if args.blog:
            print(f"   Blog: {args.blog}")
        if args.max_articles:
            print(f"   Max articles: {args.max_articles}")
    
    # Interactive menu mode
    while True:
        choice = show_menu()
        
        if choice == 1:
            run_rss_scrape(args)
            break
        elif choice == 2:
            run_category_scrape(args)
            # Ask if user wants to continue
            cont = input("\nReturn to menu? (y/n): ").strip().lower()
            if cont != 'y':
                break
        elif choice == 3:
            run_single_article_scrape(args)
            # Ask if user wants to continue
            cont = input("\nReturn to menu? (y/n): ").strip().lower()
            if cont != 'y':
                break
        elif choice == 4:
            print("\nGoodbye! 👋")
            break


if __name__ == "__main__":
    main()
