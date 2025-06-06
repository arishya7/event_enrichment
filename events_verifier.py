import os
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
print("DEBUG: Starting script...")  # Debug initial startup

def load_existing_results(output_file: str) -> list:
    """Load existing results from file or return empty list if file doesn't exist"""
    try:
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
                print(f"DEBUG: Loaded {len(existing_results)} existing events from {output_file}")
                return existing_results
        else:
            print(f"DEBUG: No existing results file found at {output_file}")
            return []
    except json.JSONDecodeError as e:
        print(f"WARNING: Error loading existing results from {output_file}: {e}")
        return []
    except Exception as e:
        print(f"WARNING: Unexpected error loading {output_file}: {e}")
        return []

def save_results(results: list, output_file: str) -> bool:
    """Save results to file, return True if successful"""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"DEBUG: Successfully saved {len(results)} events to {output_file}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save results to {output_file}: {e}")
        return False

def clean_response_text(raw_text: str) -> str:
    """
    Clean the response text by removing markdown code blocks and extra whitespace.
    Args:
        raw_text: The raw text from the API response
    Returns:
        Cleaned text with markdown and whitespace removed
    """
    if not isinstance(raw_text, str):
        print(f"WARNING: Expected string input, got {type(raw_text)}")
        return "[]"
    
    cleaned_text = raw_text.strip()
    
    # Remove markdown code blocks
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    
    return cleaned_text.strip()

def parse_response_with_recovery(response_text: str, is_final_try: bool = False) -> list:
    """
    Parse the response text into a list of dictionaries, with error recovery for malformed elements.
    Args:
        response_text: The cleaned response text
        is_final_try: Whether this is the final retry attempt
    Returns:
        List of successfully parsed event dictionaries
    """
    if not isinstance(response_text, str):
        print(f"WARNING: Expected string input, got {type(response_text)}")
        return []

    cleaned_text = clean_response_text(response_text)
    
    # If it's just an empty list, return early
    if cleaned_text.strip() in ["[]", ""]:
        print("DEBUG: Response was empty list or empty string")
        return []

    # Try to parse the entire response first
    try:
        parsed_result = json.loads(cleaned_text)
        if isinstance(parsed_result, list):
            return parsed_result
        elif isinstance(parsed_result, dict):
            return [parsed_result]
        else:
            print(f"WARNING: Unexpected JSON type: {type(parsed_result)}")
            return []
    except json.JSONDecodeError:
        # Only attempt recovery on final try
        if not is_final_try:
            print("DEBUG: JSON parsing failed, will retry with clean text")
            return []
        
        print("DEBUG: Attempting to recover partial results...")
        
        # Try to extract individual JSON objects
        recovered_events = []
        current_object = ""
        object_level = 0
        
        # Split by newlines to process line by line
        lines = cleaned_text.split('\n')
        for line_num, line in enumerate(lines, 1):
            current_object += line + '\n'
            
            # Count brackets to track JSON object boundaries
            object_level += line.count('{') - line.count('}')
            
            # If we've found a complete object
            if object_level == 0 and current_object.strip():
                try:
                    event_dict = json.loads(current_object)
                    if isinstance(event_dict, dict):
                        recovered_events.append(event_dict)
                    elif isinstance(event_dict, list):
                        recovered_events.extend(event_dict)
                except json.JSONDecodeError:
                    print(f"WARNING: Skipping malformed event at line {line_num}:")
                    print(f"Malformed JSON: {current_object[:200]}...")  # Print first 200 chars
                current_object = ""

        print(f"DEBUG: Recovered {len(recovered_events)} events from partial parsing")
        return recovered_events

def verify_events_details(prompt: str, google_api_key: str, model: str) -> list:
    """
    Calls Gemini API and handles JSON parsing of the response.
    Returns a list of event dictionaries or empty list if no events found/error occurs.
    """
    print(f"DEBUG: Calling Gemini API with model {model}")
    client = genai.Client(api_key=google_api_key)
    
    model_id = "gemini-2.5-flash-preview-05-20"
    print(f"DEBUG: Using model_id: {model_id}")

    url_context_tool = [Tool(url_context = types.UrlContext), Tool(google_search = GoogleSearch)]

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=GenerateContentConfig(
                tools=url_context_tool,
                response_modalities=["TEXT"],
            )
        )
        print("DEBUG: Got response from Gemini API")

        if not (response and response.candidates and response.candidates[0].content.parts):
            print("DEBUG: Response structure was incomplete")
            return []

        # Get raw text from response
        raw_text = response.candidates[0].content.parts[0].text
        print(f"DEBUG: Raw text from API (first 100 chars): {raw_text[:100]}")
        
        return parse_response_with_recovery(raw_text, False)  # Not final try
            
    except Exception as e:
        print(f"ERROR in verify_events_details: {str(e)}")
        return []

def main():
    print("DEBUG: Starting main function")
    output_file = "result_list.json"
    
    # Load existing results at start
    result_list = load_existing_results(output_file)
    initial_event_count = len(result_list)
    print(f"DEBUG: Starting with {initial_event_count} existing events")

    website_list = []
    file = "articles_output/sassymamasg_articles.json"
    
    try:
        with open(file, "r", encoding="utf-8") as f:
            articles = json.load(f)[10:20]
            print(f"DEBUG: Loaded {len(articles)} articles")
    except Exception as e:
        print(f"ERROR loading articles: {str(e)}")
        return

    for article in articles:
        if "article_website" in article:
            website_list.append(article["article_website"])
        else:
            print(f"WARNING: Article missing website URL: {article}")
            continue

    print(f"DEBUG: Processing {len(website_list)} websites")

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("ERROR: No Google API key found")
        return

    try:
        with open("schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)
            print("DEBUG: Loaded schema successfully")
    except Exception as e:
        print(f"ERROR loading schema: {str(e)}")
        return

    for website in website_list:
        print(f"\nDEBUG: Processing website: {website}")
        prompt = f"""
        Reading this article: {website}, extract all events details in the following format: {schema}, without \'\'\'json\'\'\'. 
        Contain all events (even if singular) in a list. 
        Return \"[]\" there is no event stated in the article. 
        For the url field, search for the event url.
        """
        
        retries = 0
        last_response = None  # Store the last response for final try recovery
        
        while retries < 3:
            print(f"DEBUG: Attempt {retries + 1} for {website}")
            result = verify_events_details(prompt, google_api_key, "gemini-2.0-flash")
            
            if result:  # If we got valid events
                result_list.extend(result)
                if save_results(result_list, output_file):
                    print(f"SUCCESS: Added {len(result)} new events from {website}")
                    print(f"DEBUG: Total events now: {len(result_list)}")
                else:
                    print(f"WARNING: Failed to save after processing {website}")
                break  # Success, move to next website
            else:
                retries += 1
                if retries == 3 and last_response:
                    # Try partial parsing on final attempt
                    print("DEBUG: Attempting partial parsing on final try")
                    final_result = parse_response_with_recovery(last_response, True)
                    if final_result:
                        result_list.extend(final_result)
                        if save_results(result_list, output_file):
                            print(f"SUCCESS: Recovered {len(final_result)} events on final try from {website}")
                            print(f"DEBUG: Total events now: {len(result_list)}")
                    else:
                        print(f"ERROR: Failed to recover any events after 3 attempts for {website}")

    final_event_count = len(result_list)
    new_events_added = final_event_count - initial_event_count
    print(f"\nDEBUG: Processing complete.")
    print(f"Initial events: {initial_event_count}")
    print(f"New events added: {new_events_added}")
    print(f"Final total: {final_event_count}")

if __name__ == "__main__":
    main()