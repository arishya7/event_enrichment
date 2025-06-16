import os
import json
from pathlib import Path
from dotenv import load_dotenv
import time
import re

from articles_extractor import *
from events_extractor import *
from address_extractor import *

def create_timestamp():
    """Create a single timestamp for the entire run"""
    current_time = time.strftime("%Y%m%d_%H%M%S")
    return current_time

def main():
    # Generate a single timestamp for this run
    run_timestamp = create_timestamp()
    
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("cx")
    blog_dict = {}

    # Read blog URLs line by line
    with open("blog_websites.txt", "r") as f:
        for line in f:
            if line.strip():
                blog_url, blog_name = line.strip().split(",")
                blog_dict[blog_name] = {"blog_url": blog_url}

    # Create RSS_temp directory if it doesn't exist
    os.makedirs('RSS_temp', exist_ok=True)

    ##############################################
    # Create timestamp directory for this run
    ##############################################
    # Create directory structure once for this run
    event_dir = Path('events_output')
    timestamp_dir = event_dir / run_timestamp
    timestamp_dir.mkdir(parents=True, exist_ok=True)
    print("This run timestamp is: ", run_timestamp)
    # Create images directory in timestamp folder
    images_dir = timestamp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    
    ##############################################
    # Extract RSS feeds as save to rss_temp folder
    ##############################################
    for blog_name, blog_details in blog_dict.items():
        filename = blog_name + '.xml'
        blog_dict[blog_name]["rss_file_path"] = os.path.join('RSS_temp', filename)
        
    #UNCOMMENT FOR DEPLOYMENT
    #     blog_dict[blog_name]["rss_file_path"] = extract_rss_feed(blog_details["blog_url"], filename)
    
    
    ##############################################
    # Extract articles from RSS feeds as json
    ##############################################
    meta_db = MetaDatabase()
    meta_db.current_run["timestamp"] = run_timestamp  # Use the same timestamp throughout
    

    for blog_name, blog_details in blog_dict.items():
        

        articles = parse_rss_file(blog_details['rss_file_path'], blog_name, meta_db)
        if articles:
            if blog_name == "honeykidsasia":
                top_few_articles = articles[25:27]
            else:
                top_few_articles = articles[50:52]
            # top_few_articles = articles[15:50] 
            articles_filename = f"{blog_name}_articles.json"
            article_file_path = save_to_json(top_few_articles, articles_filename)
            blog_dict[blog_name]['article_file_path'] = article_file_path
        elif articles == []:
            print("No events extracted")
        else:
            print("No new articles found")
    print("\n")

    #############################################
    # Extract events from articles as json
    #############################################
    for blog_name, blog_details in blog_dict.items():
        if 'article_file_path' not in blog_details or blog_details['article_file_path'] is None:
            print(f"No new articles found for {blog_name}")
            continue

        # Create blog-specific images directory
        blog_images_dir = images_dir / blog_name
        blog_images_dir.mkdir(parents=True, exist_ok=True)
        
        article_file_path = blog_details['article_file_path']
        articles_ls = json.load(open(article_file_path, 'r', encoding='utf-8'))
        if not articles_ls:
            print(f"\n --- Error: Could not load articles data from {article_file_path} for {blog_name} ---")
            continue
        
        results_ls = []

        for i, article_dict in enumerate(articles_ls, 1):
            print(f"\nProcessing article {i}/{len(articles_ls)} from {blog_name}: {article_dict['guid']}")
            
            events_ls = extract_events(article_dict, google_api_key, "gemini-2.5-pro-preview-06-05")

            if events_ls:
                
                print("="*5+f" Found! Number of events: {len(events_ls)} "+"="*5)
                try:
                    for event in events_ls:
                        print(f"   Processing event {str(events_ls.index(event)+1)}/{len(events_ls)}: {event['title']}")
                        event['scraped_on'] = run_timestamp  # Use the same timestamp

                        # Obtain venue details
                        event = extract_venue_details(event, google_api_key)
                        print(f"   Venue details extracted")
                        ########################################################################################################
                        ########################################################################################################
                        ########################################################################################################
                        ##3##################################### Add images to the event #######################################
                        
                        image_results_ls = search_images(
                            query=event['title'],
                            api_key=google_api_key,
                            cx=cx,
                            site_to_search=event['url']
                        )

                        downloaded_image_details_ls = []
                        if image_results_ls:
                            for idx, image_link in enumerate(image_results_ls, 1):
                                filename_without_ext = f"{re.sub(r'[^a-zA-Z0-9]', '_', event['title'])}_{idx}"
                                img_file_path = blog_images_dir / filename_without_ext
                                download_result = download_image(image_link, img_file_path)
                                if download_result:
                                    downloaded_image_details_ls.append(download_result)
                            if downloaded_image_details_ls:
                                event['images'] = downloaded_image_details_ls
                            else:
                                event['images'] = []
                        else:
                            event['images'] = []
                        print(f"   {len(event['images'])} images added to event")
                        ########################################################################################################
                        ########################################################################################################
                        ########################################################################################################
                    
                    results_ls.extend(events_ls)
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON response from API for article {i}: {e}")
                    print(f"API Response Text: {events_ls[:500]}...")
                    continue
            else:
                print("-"*5+" No events found in article "+"-"*5)
        if results_ls:
            print(f"\nTotal events found: {len(results_ls)}")
            output_file = timestamp_dir / f"{blog_name}_events.json"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results_ls, f, indent=2, ensure_ascii=False)
                print(f"Results saved to {output_file}")

            except Exception as e:
                print(f"Error saving results: {e}")
        else:
            print("No events found in any articles")


    meta_db.save_current_run()

if __name__ == "__main__":
    main()