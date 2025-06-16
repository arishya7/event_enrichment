import json
import os
import shutil
from pathlib import Path

def fix_image_paths():
    # Base directory
    base_dir = Path('events_output/20250613_100921')
    images_dir = base_dir / 'images'
    source_dir = images_dir / 'thesmartlocal'  # All images are here initially
    
    # Read all JSON files
    json_files = list(base_dir.glob('*_events.json'))
    
    # Process each JSON file
    for json_file in json_files:
        print(f"\nProcessing {json_file.name}...")
        
        # Read the JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        # Process each event
        for event in events:
            if 'images' in event:
                for image in event['images']:
                    # Get the correct path from the JSON
                    correct_path = Path(image['local_path'])
                    
                    # Create the target directory if it doesn't exist
                    correct_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Always look for the image in images/thesmartlocal
                    old_path = source_dir / image['filename']
                    
                    if old_path.exists():
                        print(f"Moving {image['filename']} to {correct_path}")
                        shutil.move(str(old_path), str(correct_path))
                    else:
                        print(f"Warning: Could not find {image['filename']} in images/thesmartlocal directory")

if __name__ == "__main__":
    fix_image_paths() 