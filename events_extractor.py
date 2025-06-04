import os
from google import genai
from google.genai import types
from google.oauth2 import service_account
import json
from dotenv import load_dotenv
from pathlib import Path
import re
import json

# Import AddressExtractor and GoogleCustomSearchAPI
from address_extractor import *
from image_extractor import *

# Load environment variables
load_dotenv()

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

def extract_events(article_dict: dict, google_api_key: str, system_instruction:str) -> dict:
    '''
    Call Gemini API to generate events from a blog article.

    Args:
        article_dict (dict): In string, the data of a blog article. It is formatted as a json object.
        google_api_key (str): The API key for the Gemini API.

    Returns:
        str: The generated events in json format.
    '''
    client = genai.Client(api_key=google_api_key)
    
    generate_config = {    
        "system_instruction": system_instruction,    
        "temperature": 0.0,
        "response_mime_type": "application/json",
        "response_schema": json.load(open("event_schema_init.json"))
    }

    #####################################
    # Possibly build safety settings here
    #####################################

    try:
        article_dict['content'] = clean_text(article_dict['content'])
        prompt = json.dumps(article_dict)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=generate_config
        )
        
        if response.text:
            return json.loads(response.text)
        return None

    except Exception as e:
        print(f"Error generating content: {e}")
        return None

if __name__ == "__main__":
    system_instruction = """

    """
    model = "gemini-2.0-flash"
    def main():
        """Test events extraction with user control"""
        print("=== Events Extractor Test ===\n")
        
        # Load environment variables and get API key
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            print("❌ Error: GOOGLE_API_KEY not found in .env file")
            return
        
        print("✅ API key loaded successfully")
        
        # Look for article files in articles_output directory
        article_files = []
        articles_dir = Path("articles_output")
        
        if not articles_dir.exists():
            print("❌ articles_output directory not found")
            return
            
        for file in articles_dir.glob("*articles*.json"):
            article_files.append(file)
        
        if not article_files:
            print("❌ No article files found in articles_output directory")
            print("   Looking for files with pattern '*articles*.json'")
            return
        
        print(f"📁 Found {len(article_files)} article file(s):")
        for i, file in enumerate(article_files, 1):
            print(f"   {i}. {file.name}")
        
        # User selection
        while True:
            try:
                choice = input(f"\nSelect article file (1-{len(article_files)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    return
                
                file_index = int(choice) - 1
                if 0 <= file_index < len(article_files):
                    selected_file = article_files[file_index]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(article_files)}")
            except ValueError:
                print("❌ Please enter a valid number or 'q'")
        
        # Load selected articles
        print(f"\n📖 Loading articles from: {selected_file.name}")
        try:
            with open(selected_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            if not articles:
                print("❌ No articles found in file")
                return
                
            print(f"✅ Loaded {len(articles)} articles")
            
        except Exception as e:
            print(f"❌ Error loading articles: {e}")
            return
        
        # Show articles and let user choose
        print(f"\n📰 Available articles:")
        for i, article in enumerate(articles[:10], 1):  # Show first 10
            title = article.get('title', 'No title')[:60]
            print(f"   {i}. {title}...")
        
        if len(articles) > 10:
            print(f"   ... and {len(articles) - 10} more articles")
        
        # User selection for articles
        while True:
            try:
                print(f"\nOptions:")
                print(f"  - Enter article number (1-{len(articles)}) to process one article")
                print(f"  - Enter 'all' to process all articles")
                print(f"  - Enter 'range:X-Y' to process articles X to Y (e.g., 'range:1-5')")
                print(f"  - Enter 'q' to quit")
                
                choice = input("Your choice: ").strip()
                
                if choice.lower() == 'q':
                    return
                elif choice.lower() == 'all':
                    selected_articles = articles
                    break
                elif choice.startswith('range:'):
                    try:
                        range_part = choice.split(':')[1]
                        start, end = map(int, range_part.split('-'))
                        if 1 <= start <= end <= len(articles):
                            selected_articles = articles[start-1:end]
                            break
                        else:
                            print(f"❌ Range must be between 1 and {len(articles)}")
                    except:
                        print("❌ Invalid range format. Use 'range:X-Y'")
                else:
                    article_index = int(choice) - 1
                    if 0 <= article_index < len(articles):
                        selected_articles = [articles[article_index]]
                        break
                    else:
                        print(f"❌ Please enter a number between 1 and {len(articles)}")
            except ValueError:
                print("❌ Invalid input")
        
        # Process selected articles
        print(f"\n🔄 Processing {len(selected_articles)} article(s)...\n")
        
        total_events = 0
        for i, article in enumerate(selected_articles, 1):
            print(f"{'='*80}")
            print(f"ARTICLE {i}/{len(selected_articles)}")
            print(f"{'='*80}")
            print(f"Title: {article.get('title', 'No title')}")
            print(f"URL: {article.get('url', 'No URL')}")
            print(f"Date: {article.get('published_date', 'No date')}")
            print(f"Content preview: {article.get('content', '')[:200]}...")
            print(f"\n🔍 Extracting events...")
            
            try:
                events_result = extract_events(article, google_api_key,system_instruction)
                
                # Handle if events_result is a list (API might return list directly)
                if isinstance(events_result, list):
                    events = events_result # Assume the list itself is the list of events
                    print(f"✅ Found {len(events)} event(s) (returned as a direct list):")
                elif events_result and isinstance(events_result, dict) and events_result.get('events'):
                    events = events_result['events']
                    print(f"✅ Found {len(events)} event(s) (from dict key 'events'):")
                else:
                    events = [] # No events found or unexpected format
                    print("⚠️  No events found in this article or unexpected API response format")

                if events: # Proceed only if events list is not empty
                    for j, event in enumerate(events, 1):
                        # Ensure each event item is a dictionary before using .get()
                        if not isinstance(event, dict):
                            print(f"   ⚠️  Skipping invalid event item (not a dict): {event}")
                            continue
                            
                        print(f"\n   📅 EVENT {j}:")
                        print(f"   Title: {event.get('title', 'No title')}")
                        print(f"   Description: {event.get('description', 'No description')[:200]}...")
                        print(f"   Venue: {event.get('venue', 'No venue')}")
                        print(f"   Date: {event.get('event_date', 'No date')}")
                        print(f"   Time: {event.get('event_time', 'No time')}")
                        print(f"   URL: {event.get('url', 'No URL')}")
                        print(f"   Price: {event.get('price', 'No price')}")
                        
                    total_events += len(events)
                    
            except Exception as e:
                print(f"❌ Error processing article: {e}")
            
            print(f"\n{'-'*80}\n")
        
        print(f"🎉 Processing complete!")
        print(f"📊 Total events extracted: {total_events}")
        print(f"📰 Articles processed: {len(selected_articles)}")
        
    # Run the test
    main()