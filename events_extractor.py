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
from details_extractor import *

# Load environment variables
load_dotenv()

def clean_text(text: str) -> str:
    """Clean text by removing problematic characters and normalizing whitespace."""
    if not isinstance(text, str):
        return text
    
    # First replace escaped characters
    text = text.replace('\\t', ' ').replace('\\n', ' ')
    
    # Then replace actual tab and newline characters
    text = text.replace('\t', ' ').replace('\n', ' ')
    
    # Remove a wider range of control characters except for common whitespace
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Replace multiple spaces with a single space and strip
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_events(article_dict: dict, google_api_key: str, model:str) -> list:
    client = genai.Client(api_key=google_api_key)
    
    generate_config = {    
        "system_instruction": open("system_instruction_1.txt", "r", encoding="utf-8").read(),    
        "temperature": 0.0,
        "response_mime_type": "application/json",
        "response_schema": json.load(open("event_schema_init.json"))
    }

    #####################################
    # Possibly build safety settings here
    #####################################
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            details = verify_events_details(json.dumps(article_dict), google_api_key, model)
            prompt = json.dumps(details)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=generate_config
            )
            if response.text and response.text !="[]":
                return json.loads(clean_text(response.text))
            elif response.text == "[]":
                # Retry again
                continue
            else:
                print("Response.text does not exist")
            return None # Successful but empty response

        except Exception as e:
            print(f"Error on attempt {attempt + 1}/{max_attempts}: {e}")
            if attempt < max_attempts - 1:
                print("Retrying...")
            else:
                print("Max retries reached. Failed to generate content.")
                return None
    return None

def main():
    print("=== Events Extractor Interactive CLI ===\n")

    # Prompt for API key and model
    google_api_key = input("Enter your Google API Key (or leave blank to use .env): ").strip()
    if not google_api_key:
        google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found.")
        return

    model = input("Enter the model name (default: gemini-2.5-pro-preview-05-06): ").strip()
    if not model:
        model = "gemini-2.5-pro-preview-05-06"

    # Prompt for article input
    print("\nPaste your article as JSON (or enter a file path to a JSON file):")
    article_input = input("Article JSON or file path: ").strip()

    # Try to load as file, else parse as JSON string
    article_dict = None
    if os.path.isfile(article_input):
        with open(article_input, 'r', encoding='utf-8') as f:
            article_dict = json.load(f)
    else:
        try:
            article_dict = json.loads(article_input)
        except Exception as e:
            print(f"❌ Could not parse input as JSON: {e}")
            return

    # Call extraction
    print("\nExtracting events...")
    events = extract_events(article_dict, google_api_key, model)
    print("\n=== Extraction Result ===")
    print(json.dumps(events, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()