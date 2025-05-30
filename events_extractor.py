import os
from google import genai
from google.genai import types
from google.oauth2 import service_account
import json
from dotenv import load_dotenv
from pathlib import Path

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


def load_credentials():
    """Load credentials from service account key file."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'google_key.json',
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return credentials
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def generate(input_string):
    # Set up client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY in your .env file")
    
    client = genai.Client(api_key=api_key)

    system_instruction = """
    Based on a input, which came from a online blog in Singapore, give me an output of the events. Some article may have zero, 1 or multiple events.
    The input will also contain some url links extracted from articles. Match the url link to each events as much as possible. 
    If any component of event could not be found, leave the value to NULL. 
    For description of each event, summarise the content from input. Keep it one paragraph.
    Do not mention anything about the news outline or blogging website.
    If the article does not mention anything about events or children related activities, return a blank.
    Do not include any tab, whitespace or newline in the output (with the exception of the space between words)."""

    generate_config = {    
        "system_instruction":system_instruction,    
        "temperature": 6.0,
        "top_p": 1.0,
        "response_mime_type": "application/json",
        "response_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": { "type": "string" },
                    "description": { "type": "string" },
                    "guid": { "type": "string" },
                    "url": { "type": "string", "description": "The url of the event" },
                    "price": { "type": "number" },
                    "is_free": { "type": "boolean" },
                    "start_date": { "type": "string", "format": "date-time" },
                    "end_date": { "type": "string", "format": "date-time" },
                    "venue": { "type": "object", 
                        "properties": {
                            "name": { "type": "string" },
                            "address": { "type": "string" },
                            "latitude": { "type": "number" },
                            "longitude": { "type": "number" }
                    }},
                    "organiser": { "type": "string" }
                },
                "required": ["title", "description", "guid", "url", "price", "is_free", "start_date", "end_date", "venue", "organiser"]
            }
        }
    }

    #####################################
    # Possibly build safety settings here
    #####################################

    try:
        # Generate content without streaming
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-001",
            contents=input_string,
            config=generate_config
        )
        
        # Return the complete response
        return response.text

    except Exception as e:
        print(f"Error generating content: {e}")
        return None

if __name__ == "__main__":
    # Create event_output directory if it doesn't exist
    output_dir = Path('event_output')
    output_dir.mkdir(exist_ok=True)
    
    # Example usage
    blog_website = "sassymamasg"

    # Load and process RSS data
    rss_data = load_rss(f"RSS_output/{blog_website}.json")
    articles_ls = extract_article(rss_data)
    result = generate(json.dumps(articles_ls[1]))
    
    if result:
        # Create output filename
        output_file = output_dir / f"{blog_website}_events.json"
        
        try:
            # Parse the result as JSON to validate it
            events = json.loads(result)
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            
            print(f"Results saved to {output_file}")
        except json.JSONDecodeError as e:
            print(f"Error: Result is not valid JSON: {e}")
            print("Raw result:", result)
    