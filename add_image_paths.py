#!/usr/bin/env python3
"""
Reusable script to add local_path and filename to existing image objects in JSON files.
Usage: python add_image_paths.py [json_folder] [images_folder]

Example: python add_image_paths.py data/events_output/20251015_000000 data/events_output/20251015_000000/images
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

def add_local_paths_to_json(json_folder_path, images_folder_path):
    """
    Add local_path and filename to existing image objects while preserving all other data.
    
    Args:
        json_folder_path (str): Path to folder containing JSON files
        images_folder_path (str): Path to folder containing images
    """
    json_path = Path(json_folder_path)
    images_path = Path(images_folder_path)
    
    print(f"JSON folder: {json_path}")
    print(f"Images folder: {images_path}")
    
    if not json_path.exists():
        print(f"Error: JSON folder not found: {json_path}")
        return False
    
    if not images_path.exists():
        print(f"Error: Images folder not found: {images_path}")
        return False
    
    # Create a map of all available image filenames in the images folder
    available_images = {}
    for image_file in images_path.glob("*"):
        if image_file.is_file() and image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']:
            filename = image_file.name
            available_images[filename] = image_file
    
    print(f"Found {len(available_images)} image files in {images_path}")
    
    # Process each JSON file
    total_updated = 0
    for json_file in json_path.glob("*.json"):
        print(f"\nProcessing {json_file.name}...")
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        updated_count = 0
        
        # Update each event with its images
        for event in events:
            event_id = str(event.get('id', ''))
            
            # Get existing images
            existing_images = event.get('images', [])
            
            if not existing_images:
                print(f"  Event {event_id}: No existing images found, skipping")
                continue
            
            # Create relative path from data folder
            relative_path = str(images_path.relative_to(Path("data")))
            # Replace backslashes with forward slashes for cross-platform compatibility
            relative_path_normalized = relative_path.replace('\\', '/')
            
            # Update each image by searching for its filename
            images_updated = 0
            for i, existing_img in enumerate(existing_images):
                if not isinstance(existing_img, dict):
                    continue
                
                # Get existing filename from JSON
                existing_filename = existing_img.get('filename', '')
                
                if existing_filename:
                    # Search for this filename in available images
                    if existing_filename in available_images:
                        # File found - update local_path to point to it
                        image_file = available_images[existing_filename]
                        existing_img['local_path'] = f"{relative_path_normalized}/{existing_filename}"
                        existing_img['filename'] = existing_filename  # Ensure filename is set
                        images_updated += 1
                        print(f"  Event {event_id}, Image {i+1}: Found and updated path for '{existing_filename}'")
                    else:
                        # Filename not found - try case-insensitive search
                        found_file = None
                        for available_filename, image_file in available_images.items():
                            if available_filename.lower() == existing_filename.lower():
                                found_file = (available_filename, image_file)
                                break
                        
                        if found_file:
                            # Found with different case - update both filename and path
                            correct_filename, image_file = found_file
                            existing_img['local_path'] = f"{relative_path_normalized}/{correct_filename}"
                            existing_img['filename'] = correct_filename
                            images_updated += 1
                            print(f"  Event {event_id}, Image {i+1}: Found '{correct_filename}' (case mismatch), updated filename and path")
                        else:
                            print(f"  Event {event_id}, Image {i+1}: Warning - filename '{existing_filename}' not found in images folder")
                else:
                    # No filename in JSON - skip this image
                    print(f"  Event {event_id}, Image {i+1}: No filename specified, skipping")
            
            if images_updated > 0:
                updated_count += 1
        
        # Save updated JSON
        if updated_count > 0:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            print(f"  Saved {json_file.name} with {updated_count} updated events")
            total_updated += updated_count
        else:
            print(f"  No events updated in {json_file.name}")
    
    print(f"\n✅ Update complete! Total events updated: {total_updated}")
    return True

if __name__ == "__main__":
    if len(sys.argv) == 3:
        json_folder = sys.argv[1]
        images_folder = sys.argv[2]
    else:
        print("Usage: python add_image_paths.py [json_folder] [images_folder]")
        print("\nExamples:")
        print("  python add_image_paths.py data/events_output/20251015_000000 data/events_output/20251015_000000/images")
        print("  python add_image_paths.py data/events_output/20250120_000000 data/events_output/20250120_000000/images")
        sys.exit(1)
    
    print("Adding local_path and filename to existing image objects...")
    add_local_paths_to_json(json_folder, images_folder)

