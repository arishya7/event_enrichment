import json
import os
from pathlib import Path
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Schema for event extraction
schema = """
{
    "title": "Event",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "price": {"type": "number"},
        "is_free": {"type": "boolean"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "venue": {"type": "string"},
        "organiser": {"type": "string"}
    },
    "required": ["title", "description", "price", "is_free", "start_date", "end_date", "venue", "organiser"]
}
"""

def truncate_text(text, max_chars=1500):
    """Truncate text to a maximum number of characters while trying to keep complete sentences."""
    if len(text) <= max_chars:
        return text
    
    # Try to find the last sentence boundary before max_chars
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > 0:
        return truncated[:last_period + 1]
    return truncated

def process_rss_entries(json_file_path):
    # Check for Hugging Face API token
    hf_token = os.getenv('HUGGINGFACE_API_TOKEN')
    if not hf_token:
        raise ValueError("Please set HUGGINGFACE_API_TOKEN in your .env file")
    
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        rss_data = json.load(file)
    
    # Initialize the Hugging Face client with API token
    client = InferenceClient(token=hf_token)
    
    processed_events = []
    
    # Process each entry in the RSS data
    for entry in rss_data.get('articles', []):
        title = entry.get('title', '')
        content = entry.get('content', '')
        
        # Skip if no content
        if not content:
            print(f"Skipping entry with no content: {title}")
            continue
            
        # Create a prompt from the entry content
        prompt = f"""Extract event information from the following text and format it as JSON. If the text does not contain event information, return null.
The JSON should follow this schema:
{schema}

Text to analyze:
Title: {title}
Content: {truncate_text(content, 1000)}

Return only valid JSON that matches the schema, or null if no event information is found.
"""
        
        try:
            # Generate structured event data using the Hugging Face API
            response = client.text_generation(
                prompt,
                model="mistralai/Mixtral-8x7B-Instruct-v0.1",
                max_new_tokens=1000,
                temperature=0.1,
                return_full_text=False
            )
            
            # Parse the response as JSON
            try:
                # Clean up the response to extract just the JSON part
                json_str = response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                    
                event = json.loads(json_str.strip())
                if event:
                    processed_events.append(event)
                    print(f"Successfully processed: {title}")
            except json.JSONDecodeError as je:
                print(f"Error parsing JSON response for entry: {title}")
                print(f"Response was: {response[:200]}...")
                continue
                
        except Exception as e:
            print(f"Error processing entry: {title}")
            print(f"Error details: {str(e)}")
            continue
    
    # Save the processed events to a file
    output_dir = Path('event_output')
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{Path(json_file_path).stem}_processed.json"
    with open(output_file, 'w') as f:
        json.dump(processed_events, f, indent=2)
    
    print(f"\nProcessed {len(processed_events)} events. Saved to {output_file}")

if __name__ == "__main__":
    # Process all JSON files in the RSS_output directory
    rss_dir = Path("RSS_output")
    for json_file in rss_dir.glob("*.json"):
        process_rss_entries(str(json_file))