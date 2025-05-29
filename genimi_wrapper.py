import os
from google import generativeai as genai
from google.oauth2 import service_account
import json
from rss_extractor import load_rss, extract_article

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
    client = genai.Client(api_keys=os.getenv("GOOGLE_API_KEY"))

    system_instruction = """
    Based on a input, which came from a online blog in Singapore, give me an output of the events. Some article may have zero, 1 or multiple events.
    The input will also contain some url links extracted from articles. Match the url link to each events as much as possible. 
    If any component of event could not be found, leave the value to NULL. 
    For description of each event, summarise the content from input. Keep it one paragraph.
    Do not mention anything about the news outline or blogging website.
    If the article does not mention anything about events or children related activities, return a blank."""

    generate_config = {        
        "temperature": 1.0,
        "top_p": 1.0,
        "response_mime_type": "application/json",
        "response_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": { "type": "string" },
                    "description": { "type": "string" },
                    "price": { "type": "number" },
                    "is_free": { "type": "boolean" },
                    "start_date": { "type": "string" },
                    "end_date": { "type": "string" },
                    "venue": { "type": "string" },
                    "organiser": { "type": "string" }
                },
                "required": ["title", "description", "price", "is_free", "start_date", "end_date", "venue", "organiser"]
            }
        }
    }
    # Configure safety settings
    safety_settings = {
        "HARM_CATEGORY_HATE_SPEECH": "OFF",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "OFF",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "OFF",
        "HARM_CATEGORY_HARASSMENT": "OFF"
    }

    try:
        # Generate content without streaming
        response = client.generate_content(
            model="gemini-2.0-flash-lite-001",
            contents=input_string,
            generation_config=generate_config,
            safety_settings=safety_settings
        )
        
        # Return the complete response
        return response.text

    except Exception as e:
        print(f"Error generating content: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    rss_data = load_rss("RSS_output/sassymamasg.json")
    articles_ls = extract_article(rss_data)
    result = generate(json.dumps(articles_ls[0]))
    if result:
        print(result)