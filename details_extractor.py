import os
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, UrlContext
import json
from dotenv import load_dotenv
from pathlib import Path


def verify_events_details(prompt: str, google_api_key: str, model: str) -> str:
    """
    Calls Gemini API and handles JSON parsing of the response.
    Returns a list of event dictionaries or empty list if no events found/error occurs.
    Will retry up to 2 times if response text is missing or empty.
    """
    client = genai.Client(api_key=google_api_key)
    tools = [Tool(url_context = UrlContext), Tool(google_search = GoogleSearch)]
    max_retries = 1
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # Make API call
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=GenerateContentConfig(
                    system_instruction=open("system_instruction_1.txt", "r", encoding="utf-8").read(),
                    tools=tools,
                    response_modalities=["TEXT"],
                )
            )            
            # Check if response is valid
            if not response:
                print(f"Error: Empty response from API (Attempt {retry_count + 1}/{max_retries +1})")
                retry_count += 1
                continue

            # Try to get text directly from response.text
            try:
                if hasattr(response, 'text') and response.text:
                    return response.text
                
                print(f"Response.text missing or empty (Attempt {retry_count + 1}/{max_retries + 1})")
                retry_count += 1
                continue

            except Exception as e:
                print(f"Error extracting text from response: {e}")
                retry_count += 1
                continue

        except Exception as e:
            print(f"ERROR in verify_events_details: {str(e)}")
            retry_count += 1
            if retry_count <= max_retries:
                print(f"Retrying... (Attempt {retry_count + 1}/{max_retries + 1})")
                continue
            return ""

    print("All retry attempts exhausted")
    return ""

def test_verify_events_details():
    """Test function to verify the functionality of verify_events_details()"""
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    model = "gemini-2.5-pro"
    
    # Test case 1: Valid input
    test_input = {
        "title": "Test Event",
        "description": "This is a test event description",
        "url": "https://example.com/test-event"
    }
    result = verify_events_details(json.dumps(test_input), google_api_key, model)
    print("\nTest Case 1 - Valid Input:")
    print(f"Input: {test_input}")
    print(f"Result: {result}")
    
    # Test case 2: Empty input
    empty_input = {}
    result = verify_events_details(json.dumps(empty_input), google_api_key, model)
    print("\nTest Case 2 - Empty Input:")
    print(f"Input: {empty_input}")
    print(f"Result: {result}")
    
    # Test case 3: Invalid API key
    result = verify_events_details(json.dumps(test_input), "invalid_key", model)
    print("\nTest Case 3 - Invalid API Key:")
    print(f"Input: {test_input}")
    print(f"Result: {result}")

def main():
    """Interactive test function for details verification"""
    print("=== Details Extractor Test ===\n")
    
    # Load environment variables and get API key
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found in .env file")
        return
    
    print("✅ API key loaded successfully")
    
    # Look for article files in articles_output directory
    article_files = []
    articles_dir = Path("articles_output")
    
    if not articles_dir.exists():
        print("Articles_output directory not found")
        return
        
    for file in articles_dir.glob("*articles*.json"):
        article_files.append(file)
    
    if not article_files:
        print("No article files found in articles_output directory")
        print("Looking for files with pattern '*articles*.json'")
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
                print(f"Please enter a number between 1 and {len(article_files)}")
        except ValueError:
            print("Please enter a valid number or 'q'")
    
    # Load selected articles
    print(f"\nLoading articles from: {selected_file.name}")
    try:
        with open(selected_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        if not articles:
            print("No articles found in file")
            return
            
        print(f"Loaded {len(articles)} articles")
        
    except Exception as e:
        print(f"Error loading articles: {e}")
        return
    
    # Show articles and let user choose
    print(f"\nAvailable articles:")
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
    
    model = "gemini-2.0-flash"
    for i, article in enumerate(selected_articles, 1):
        print(f"{'='*80}")
        print(f"ARTICLE {i}/{len(selected_articles)}")
        print(f"{'='*80}")
        print(f"Title: {article.get('title', 'No title')}")
        print(f"Content preview: {article.get('content', '')[:500]}...")
        print(f"\n🔍 Verifying details...")
        
        try:
            result = verify_events_details(json.dumps(article), google_api_key, model)
            print(f"\n✅ Verification Result:")
            print(f"{result}")
            
        except Exception as e:
            print(f"❌ Error processing article: {e}")
        
        print(f"\n{'-'*80}\n")
    
    print(f"🎉 Processing complete!")
    print(f"📰 Articles processed: {len(selected_articles)}")

if __name__ == "__main__":
    main()