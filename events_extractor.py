import os
from google import genai
from google.genai import types
from google.oauth2 import service_account
import json
from dotenv import load_dotenv
from pathlib import Path
import re

# Import AddressExtractor and GoogleCustomSearchAPI
from address_extractor import *
from image_extractor import *

# Load environment variables
load_dotenv()

import json

def load_rss(file_path):
    """Load and parse JSON data from RSS output file.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: Parsed JSON data as a dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None
    
def extract_article(rss_data):
    articles = rss_data.get('articles', [])
    return articles

def clean_text(text: str) -> str:
    """Clean text by removing problematic characters and normalizing whitespace."""
    if not isinstance(text, str):
        return text
    
    # Remove tabs, newlines, and other common problematic whitespace
    text = text.replace('\\t', '').replace('\\n', '').replace('\t', '').replace('\n', '')
    
    # Remove a wider range of control characters except for common whitespace
    # This regex matches most ASCII control characters but keeps space, tab, newline, carriage return
    text = re.sub(r'[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]', '', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\\s+', ' ', text).strip()
    
    return text

def generate(prompt:str) -> str:
    '''
    Call Gemini API to generate events from a blog article.

    Args:
        prompt (str): In string, the data of a blog article. It is formatted as a json object.

    Returns:
        str: The generated events in json format.
    '''
    # Set up client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY in your .env file")
    
    client = genai.Client(api_key=api_key)

    system_instruction = """
    Based on an input, which came from an online blog in Singapore, your task is to identify and extract information about specific, one-time events suitable for children and families.

    CRITICAL CRITERIA FOR EVENT EXTRACTION:
    1.  EVENT TYPE: The event must be a distinct activity, festival, performance, exhibition, or special occurrence. It should NOT be an ongoing class, a regular course, a routine service offered by a business, or a general venue opening.
    2.  TIME-BOUND: The event should ideally have a specific date, a limited run (e.g., a weekend festival), or be clearly described as a one-off. Avoid activities that are part of a regular weekly/monthly schedule or continuously available.
    3.  CONTENT FOCUS: The article's main purpose should be to describe this specific event.
        You MUST SKIP THE ENTIRE ARTICLE and return no events if the article primarily:
        a. Promotes general business services, products, or a list of businesses.
        b. Functions as a directory, roundup, or listicle of multiple businesses offering similar ongoing services (e.g., an article titled 'Best Art Classes in Singapore' that lists various studios and their regular class schedules, or 'Top Playgrounds').
        c. Describes general amenities of a place (like a park or museum) without highlighting a unique, specific event happening there.
        d. Road show type of events with multiple locations and multiple dates.
    4.  LOCATION: The event must have a discernible location mentioned in the article. If no location can be found for a potential event, skip that event.

    OUTPUT REQUIREMENTS:
    -   Some articles may contain zero, one, or multiple distinct, qualifying one-time events. Extract all such events.
    -   If any required component for a qualifying event (as per the schema) cannot be found in the article, leave the value for that component as NULL.
    -   For the description of each extracted event, rephrase the content from the input. Do not copy verbatim for extended lengths.
    -   Do not mention the news outlet, author, or blogging website in your output.
    """

    schema = json.load(open("event_schema_init.json"))
    
    generate_config = {    
        "system_instruction": system_instruction,    
        "temperature": 0.0,
        "response_mime_type": "application/json",
        "max_tokens": 8192,
        "response_schema": schema
    }

    #####################################
    # Possibly build safety settings here
    #####################################

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-001",
            contents=prompt,
            config=generate_config
        )
        
        if response.text:
            # No need to re-clean here as the API should return clean JSON
            # based on its schema. If API returns malformed JSON, that's a different issue.
            return response.text # Return raw API response text
        return None

    except Exception as e:
        print(f"Error generating content: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    blog_website = "theasianparent"

    # Create events_output directory and images directory
    output_dir = Path('events_output')
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = Path(f"events_output/images/{blog_website}")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Load and process RSS data
    articles_file = Path(f"articles_output/{blog_website}_articles.json")
    if not articles_file.exists():
        print(f"Error: Articles file not found at {articles_file}")
        exit(1)

    articles_ls = load_rss(str(articles_file))
    if not articles_ls:
        print("Error: Could not load articles data")
        exit(1)

    # Initialize AddressExtractor with minimal configuration
    try:
        address_extractor = AddressExtractor(
            headers={'Content-Type': 'application/json'},
            body_template={}  # No location bias as requested
        )
    except ValueError as ve:
        print(f"Error initializing AddressExtractor: {ve}. Make sure GOOGLE_MAPS_API_KEY is set.")
        exit(1)

    # Initialize GoogleCustomSearchAPI
    try:
        search_api = GoogleCustomSearchAPI()
    except ValueError as e:
        print(f"Error initializing GoogleCustomSearchAPI: {e}")
        exit(1)

    print(f"Processing {len(articles_ls)} articles...")
    results_ls = []
    image_mapping = {}
    
    for i, article_orig in enumerate(articles_ls[:3], 1):
        print(f"Processing article {i}/{len(articles_ls)}")
        
        # Create a deep copy to modify for the API call
        article_for_api = json.loads(json.dumps(article_orig)) 

        # Apply more aggressive cleaning to the 'content' field
        if 'content' in article_for_api and isinstance(article_for_api['content'], str):
            article_for_api['content'] = clean_text(article_for_api['content'])

        article_prompt = json.dumps(article_for_api)
            
        result_text = generate(article_prompt) # Pass the cleaned string
        if result_text:
            try:
                # The API response should be valid JSON according to the schema
                events = json.loads(result_text) 
                if isinstance(events, list) and events:
                    
                    for event in events:
                        event_title = event.get('title', '')
                        event_venue = event.get('venue')
                    
                        # Add address to the event
                        search_query = f"{event_title} {event_venue}" if event_title else event_venue
                        address_details = address_extractor.extract_address_details(search_query)
                        event['full_address'] = address_details.get('address')
                        event['latitude'] = address_details.get('latitude')
                        event['longitude'] = address_details.get('longitude')
                    
                        # Add images to the event
                        print(f"Searching images for: {event_title}")
                        image_results = search_api.search_images(
                            query=event_title,
                            num_results=5,
                            site_to_search=event.get('url')
                        )

                        if image_results:
                            downloaded_image_details = search_api.download_images(
                                image_download_dir=images_dir,
                                image_results=image_results,
                                event_title_for_filename=event_title,
                                num_to_download=5  # Same as in main()
                            )
                            
                            if downloaded_image_details:
                                event['images'] = downloaded_image_details
                                image_mapping[event_title] = downloaded_image_details

                    # Add all processed events to results
                    results_ls.extend(events)
                    print(f"Found {len(events)} events in article {i}")
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON response from API for article {i}: {e}")
                print(f"API Response Text: {result_text[:500]}...") # Print beginning of problematic response
                continue

    if results_ls:
        print(f"\nTotal events found: {len(results_ls)}")
        output_file = output_dir / f"{blog_website}_events.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_ls, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {output_file}")

            # Save image mapping
            with open(output_dir / "images" / "image_mapping.json", 'w', encoding='utf-8') as f:
                json.dump(image_mapping, f, indent=2)
            print("Image mapping saved")
        except Exception as e:
            print(f"Error saving results: {e}")
    else:
        print("No events found in any articles")
    