import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
import time
from urllib.error import URLError

from articles_extractor import *
from events_extractor import *

def main():
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
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
            print(f"Saved top {len(top_20_articles)} articles (out of {len(articles)} new articles found based on RSS order)")
        else:
            print("No new articles found")
    meta_db.save_current_run()

    #############################################
    # Extract events from articles as json
    #############################################
    event_dir = Path('events_output')
    event_dir.mkdir(parents=True, exist_ok=True)
    
    for blog_name, blog_details in blog_dict.items():
        images_dir = Path(f"events_output/images/{blog_name}")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        article_file_path = blog_details['article_file_path']
        articles_ls = load_rss(article_file_path)  
        if not articles_ls:
            print("Error: Could not load articles data")
            exit(1)
        
        address_extractor = AddressExtractor(headers={'Content-Type': 'application/json'}, body_template={})
        search_api = GoogleCustomSearchAPI()

        results_ls = []
        image_mapping = {}

        for i, article_orig in enumerate(articles_ls, 1):
            print(f"Processing article {i}/{len(articles_ls)}")
            
            # Create a deep copy to modify for the API call
            article_for_api = json.loads(json.dumps(article_orig)) 

            # Apply more aggressive cleaning to the 'content' field
            if 'content' in article_for_api and isinstance(article_for_api['content'], str):
                article_for_api['content'] = clean_text(article_for_api['content'])

            article_prompt = json.dumps(article_for_api)
            result_text = generate(article_prompt)

            if result_text:
                try:
                    events = json.loads(result_text)
                    if isinstance(events, list) and events:
                        for event in events:
                            event_title = event.get('title', '')
                            event_venue = event.get('venue')
                            event_url = event.get('url')

                            # Add address to the event
                            search_query = f"{event_title} {event_venue}" if event_title else event_venue
                            address_details = address_extractor.extract_address_details(search_query)
                            event['full_address'] = address_details.get('address')
                            event['latitude'] = address_details.get('latitude')
                            event['longitude'] = address_details.get('longitude')

                            # Add images to the event
                            num_img = 5
                            image_results = search_api.search_images(
                                query=event_title,
                                num_results=num_img,
                                site_to_search="NULL"
                            )

                            if image_results:
                                downloaded_image_details = search_api.download_images(
                                    image_download_dir=images_dir,
                                    image_results=image_results,
                                    event_title_for_filename=event_title,
                                    num_to_download=num_img
                                )

                                if downloaded_image_details:
                                    event['images'] = downloaded_image_details
                                    image_mapping[event_title] = downloaded_image_details
                        
                        results_ls.extend(events)
                        print(f"Found {len(events)} events in article {i}")
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON response from API for article {i}: {e}")
                    print(f"API Response Text: {result_text[:500]}...")
                    continue

        if results_ls:
            print(f"\nTotal events found: {len(results_ls)}")
            output_file = event_dir / f"{blog_name}_events.json"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results_ls, f, indent=2, ensure_ascii=False)
                print(f"Results saved to {output_file}")

                # Save image mapping
                with open(event_dir / "images" / "image_mapping.json", 'w', encoding='utf-8') as f:
                    json.dump(image_mapping, f, indent=2)
                print("Image mapping saved")
            except Exception as e:
                print(f"Error saving results: {e}")
        else:
            print("No events found in any articles")

if __name__ == "__main__":
    main()