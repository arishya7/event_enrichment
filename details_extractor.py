import os
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import json
from dotenv import load_dotenv
from pathlib import Path


def verify_events_details(prompt: str, google_api_key: str, model: str) -> str:
    """
    Calls Gemini API and handles JSON parsing of the response.
    Returns a list of event dictionaries or empty list if no events found/error occurs.
    """
    client = genai.Client(api_key=google_api_key)
    
    url_context_tool = [Tool(url_context = types.UrlContext), Tool(google_search = GoogleSearch)]

    try:
        # Make API call
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=open("system_instruction_1.txt", "r", encoding="utf-8").read(),
                tools=url_context_tool,
                response_modalities=["TEXT"],
            )
        )
        
        # Check if response is valid
        if not response:
            print("Error: Empty response from API")
            return ""

        # Try to get text directly from response.text first
        try:
            if hasattr(response, 'text') and response.text:
                raw_text = response.text
            else:
                print("Falling back to response.candidates[0].content.parts[0].text")
                if not response.candidates:
                    print("Error: No candidates in response")
                    return ""
                    
                if not response.candidates[0].content:
                    print("Error: No content in first candidate")
                    return ""
                    
                if not response.candidates[0].content.parts:
                    print("Error: No parts in content")
                    return ""
                
                raw_text = response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"Error extracting text from response: {e}")
            return ""
        
        return raw_text

    except Exception as e:
        print(f"ERROR in verify_events_details: {str(e)}")
        return ""

def main():
    ############################################################
    #Test
    ############################################################
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    model = "gemini-2.0-flash"
    article_file_ls = json.load(open("articles_output/honeykidsasia_articles.json", "r", encoding="utf-8"))
    result = verify_events_details(json.dumps(article_file_ls[2]), google_api_key, model)
    print(result)
    return

if __name__ == "__main__":
    main()