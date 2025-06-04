import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
import time
from urllib.error import URLError
import re
from urllib.parse import urlparse, unquote

from articles_extractor import *
from events_extractor import *
from address_extractor import *

def main():
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
    # Extract RSS feeds as save to rss_temp folder
    ##############################################
    for blog_name, blog_details in blog_dict.items():
        filename = blog_name + '.xml'
        blog_dict[blog_name]["rss_file_path"] = extract_rss_feed(blog_details["blog_url"], filename)
    
    ##############################################
    # Extract articles from RSS feeds as json
    ##############################################
    meta_db = MetaDatabase()
    for blog_name, blog_details in blog_dict.items():
        articles = parse_rss_file(blog_details['rss_file_path'], blog_name, meta_db)
        if articles:
            top_20_articles = articles[:20]
            articles_filename = f"{blog_name}_articles.json"
            article_file_path = save_to_json(top_20_articles, articles_filename)
            blog_dict[blog_name]['article_file_path'] = article_file_path
        else:
            print("No new articles found")
    meta_db.save_current_run()

    #############################################
    # Extract events from articles as json
    #############################################
    event_dir = Path('events_output')
    event_dir.mkdir(parents=True, exist_ok=True)
    
    for blog_name, blog_details in blog_dict.items():
        if 'article_file_path' not in blog_details or blog_details['article_file_path'] is None:
            print(f"No new articles found for {blog_name}")
            continue
        
        images_dir = Path(f"events_output/images/{blog_name}")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        article_file_path = blog_details['article_file_path']
        articles_ls = json.load(open(article_file_path, 'r', encoding='utf-8'))  
        if not articles_ls:
            print("Error: Could not load articles data")
            continue
        
        results_ls = []

        for i, article_dict in enumerate(articles_ls, 1):
            print(f"Processing article {i}/{len(articles_ls)}")
            
            events_ls = extract_events(article_dict, google_api_key, open("system_instruction.txt", "r").read(), "gemini-2.0-flash")

            if events_ls:
                try:
                    for event in events_ls:
                        # Obtain venue details
                        event = extract_venue_details(event, google_api_key)
                        
                        ########################################################################################################
                        ########################################################################################################
                        ########################################################################################################
                        # Add images to the event
                        image_results_ls = search_images(
                            query=event['title'],
                            api_key=google_api_key,
                            cx=cx,
                            num_results=5,
                            site_to_search=event['url']
                        )

                        downloaded_image_details_ls = []
                        if image_results_ls:
                            
                            for idx, image_item in enumerate(image_results_ls, 1):

                                filename_without_ext = f"{re.sub(r'[^a-zA-Z0-9]', '_', event['title'])}_{idx}"
                                img_file_path = images_dir / filename_without_ext
                                
                                download_result = download_image(image_item['link'], img_file_path)
                                if download_result:
                                    downloaded_image_details_ls.append(download_result)

                            if downloaded_image_details_ls:
                                event['images'] = downloaded_image_details_ls
                        ########################################################################################################
                        ########################################################################################################
                        ########################################################################################################
                    
                    results_ls.extend(events_ls)
                    print(f"Found {len(events_ls)} events in article {i}")
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON response from API for article {i}: {e}")
                    print(f"API Response Text: {events_ls[:500]}...")
                    continue

        if results_ls:
            print(f"\nTotal events found: {len(results_ls)}")
            output_file = event_dir / f"{blog_name}_events.json"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results_ls, f, indent=2, ensure_ascii=False)
                print(f"Results saved to {output_file}")

            except Exception as e:
                print(f"Error saving results: {e}")
        else:
            print("No events found in any articles")

if __name__ == "__main__":
    main()