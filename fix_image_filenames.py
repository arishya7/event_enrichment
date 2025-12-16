#!/usr/bin/env python3
"""
Fix image filenames in JSON to match actual files in images folder.
Matches images to events by title similarity and updates JSON with correct filenames.

Usage: python fix_image_filenames.py [json_folder] [images_folder]

Example: python fix_image_filenames.py data/events_output/Nov_12 data/events_output/Nov_12/images
"""

import json
import sys
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher


def normalize_title(title):
    """Normalize title for matching (remove special chars, lowercase)."""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', title.lower())
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', '_', normalized.strip())
    return normalized


def normalize_filename(filename):
    """Normalize filename for matching (remove extension, normalize)."""
    # Remove extension and normalize
    name = Path(filename).stem.lower()
    # Remove special characters
    name = re.sub(r'[^\w]', '', name)
    return name


def similarity_score(str1, str2):
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, str1, str2).ratio()


def match_images_to_events(events, image_files):
    """Match image files to events by title similarity."""
    # Group images by base name (without number suffix)
    images_by_base = defaultdict(list)
    for img_file in image_files:
        # Extract base name (e.g., "Little_Bears_House_Fun_Interactive_Learning" from "Little_Bears_House_Fun_Interactive_Learning_1.jpg")
        base_match = re.match(r'(.+?)_\d+$', img_file.stem)
        if base_match:
            base_name = base_match.group(1)
            images_by_base[base_name].append(img_file.name)
        else:
            # No number suffix, use whole name
            images_by_base[img_file.stem].append(img_file.name)
    
    # Sort images within each group
    for base in images_by_base:
        images_by_base[base].sort()
    
    # Match events to image groups
    matches = {}
    for event in events:
        event_id = str(event.get('id', ''))
        title = event.get('title', '')
        
        if not title or not event_id:
            continue
        
        # Normalize event title
        normalized_title = normalize_title(title)
        
        # Find best matching image group
        best_match = None
        best_score = 0.0
        
        for base_name, filenames in images_by_base.items():
            normalized_base = normalize_filename(base_name)
            score = similarity_score(normalized_title, normalized_base)
            
            if score > best_score and score > 0.5:  # Minimum 50% similarity
                best_score = score
                best_match = (base_name, filenames)
        
        if best_match:
            matches[event_id] = best_match[1]
    
    return matches


def fix_json_filenames(json_folder_path, images_folder_path):
    """Fix image filenames in JSON files to match actual files."""
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
    
    # Get all image files
    image_files = list(images_path.glob("*.jpg")) + list(images_path.glob("*.png")) + list(images_path.glob("*.webp"))
    print(f"Found {len(image_files)} image files")
    
    if not image_files:
        print("No image files found!")
        return False
    
    # Process each JSON file
    total_updated = 0
    for json_file in json_path.glob("*.json"):
        print(f"\nProcessing {json_file.name}...")
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        # Match images to events
        matches = match_images_to_events(events, image_files)
        print(f"  Matched {len(matches)} events to image groups")
        
        updated_count = 0
        
        # Update each event with matched images
        for event in events:
            event_id = str(event.get('id', ''))
            
            if event_id in matches:
                matched_filenames = matches[event_id]
                existing_images = event.get('images', [])
                
                if not existing_images:
                    print(f"  Event {event_id}: No existing images, skipping")
                    continue
                
                # Create relative path
                relative_path = str(images_path.relative_to(Path("data"))).replace('\\', '/')
                
                # Update images with correct filenames
                for i, existing_img in enumerate(existing_images):
                    if i < len(matched_filenames):
                        image_filename = matched_filenames[i]
                        
                        if isinstance(existing_img, dict):
                            existing_img['local_path'] = f"{relative_path}/{image_filename}"
                            existing_img['filename'] = image_filename
                        else:
                            # Convert string to dict
                            event['images'][i] = {
                                'url': existing_img if isinstance(existing_img, str) else '',
                                'local_path': f"{relative_path}/{image_filename}",
                                'filename': image_filename,
                                'source_credit': ''
                            }
                
                updated_count += 1
                print(f"  Event {event_id}: Updated {min(len(existing_images), len(matched_filenames))} images")
        
        # Save updated JSON
        if updated_count > 0:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
            print(f"  Saved {json_file.name} with {updated_count} updated events")
            total_updated += updated_count
        else:
            print(f"  No events updated in {json_file.name}")
    
    print(f"\n✅ Fix complete! Total events updated: {total_updated}")
    return True


if __name__ == "__main__":
    if len(sys.argv) == 3:
        json_folder = sys.argv[1]
        images_folder = sys.argv[2]
    else:
        print("Usage: python fix_image_filenames.py [json_folder] [images_folder]")
        print("\nExamples:")
        print("  python fix_image_filenames.py data/events_output/Nov_12 data/events_output/Nov_12/images")
        sys.exit(1)
    
    print("Fixing image filenames in JSON to match actual files...")
    fix_json_filenames(json_folder, images_folder)

