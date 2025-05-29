import outlines
import outlines.models as models
import json
import os
from pathlib import Path

schema = {
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

def process_rss_entries(json_file_path):
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        rss_data = json.load(file)
    
    # Initialize the model
    model = models.transformers("mistralai/Mistral-7B-Instruct-v0.3")
    
    # Initialize the generator
    generator = outlines.generate.json(model, schema)
    
    processed_events = []
    
    # Process each entry in the RSS data
    for entry in rss_data:
        # Create a prompt from the entry
        prompt = f"Extract event information from this text: {entry['title']} - {entry.get('description', '')}"
        
        # Generate structured event data
        event_data = generator(prompt)
        processed_events.append(event_data)
    
    # Create event_output directory if it doesn't exist
    output_dir = Path("event_output")
    output_dir.mkdir(exist_ok=True)
    
    # Save processed events to the event_output directory
    output_path = output_dir / f"processed_{Path(json_file_path).name}"
    with open(output_path, 'w') as file:
        json.dump(processed_events, file, indent=2)
    
    return processed_events

# Process all JSON files in the RSS_output directory
rss_dir = Path("RSS_output")
for json_file in rss_dir.glob("*.json"):
    process_rss_entries(str(json_file))