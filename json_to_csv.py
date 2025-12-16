#!/usr/bin/env python3
"""
Convert all JSON files in a folder to a single CSV file.
Handles nested structures like images arrays by flattening them.

Usage: python json_to_csv.py [json_folder] [output_csv]

Examples:
  python json_to_csv.py data/events_output/mall_add mall_add_events.csv
  python json_to_csv.py data/events_output/20251001_000000 events_20251001.csv
"""

import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested items
        sep: Separator for flattened keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Handle lists by converting to string or creating indexed entries
            if v and isinstance(v[0], dict):
                # If list contains dicts, create indexed entries
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}_{i}", str(item)))
            else:
                # Simple list - join as string
                items.append((new_key, '; '.join(str(x) for x in v) if v else ''))
        else:
            items.append((new_key, v))
    
    return dict(items)


def normalize_path(path: str) -> str:
    """
    Normalize file paths to use forward slashes.
    
    Args:
        path: File path to normalize
        
    Returns:
        Normalized path with forward slashes
    """
    if not path:
        return path
    return path.replace('\\', '/')


def normalize_images_format(images: List[Any]) -> List[Dict[str, Any]]:
    """
    Ensure all images are in proper JSON format with normalized paths.
    
    Args:
        images: List of image objects or URLs
        
    Returns:
        List of normalized image objects
    """
    normalized_images = []
    
    for img in images:
        if isinstance(img, str):
            # Convert string URL to proper image object
            normalized_img = {
                'url': img,
                'original_url': img,
                'filename': '',
                'local_path': '',
                'source_credit': ''
            }
        elif isinstance(img, dict):
            # Normalize existing image object
            normalized_img = {
                'url': img.get('url', ''),
                'original_url': img.get('original_url', img.get('url', '')),
                'filename': img.get('filename', ''),
                'local_path': normalize_path(img.get('local_path', '')),
                'source_credit': img.get('source_credit', '')
            }
        else:
            continue
            
        normalized_images.append(normalized_img)
    
    return normalized_images


def extract_images_info(images: List[Any]) -> Dict[str, str]:
    """
    Extract image information and create summary fields.
    
    Args:
        images: List of image objects or URLs
        
    Returns:
        Dictionary with image summary fields
    """
    if not images:
        return {
            'image_count': 0,
            'image_urls': '',
            'image_filenames': '',
            'image_local_paths': '',
            'images_json': '[]'
        }
    
    # Normalize images to proper format
    normalized_images = normalize_images_format(images)
    
    urls = []
    filenames = []
    local_paths = []
    
    for img in normalized_images:
        if img['url']:
            urls.append(img['url'])
        if img['filename']:
            filenames.append(img['filename'])
        if img['local_path']:
            local_paths.append(img['local_path'])
    
    return {
        'image_count': len(normalized_images),
        'image_urls': '; '.join(urls),
        'image_filenames': '; '.join(filenames),
        'image_local_paths': '; '.join(local_paths),
        'images_json': json.dumps(normalized_images, ensure_ascii=False)
    }


def process_json_files(json_folder_path: str, output_csv_path: str) -> bool:
    """
    Process all JSON files in a folder and convert to CSV.
    
    Args:
        json_folder_path: Path to folder containing JSON files
        output_csv_path: Path for output CSV file
        
    Returns:
        True if successful, False otherwise
    """
    json_path = Path(json_folder_path)
    output_path = Path(output_csv_path)
    
    print(f"JSON folder: {json_path}")
    print(f"Output CSV: {output_path}")
    
    if not json_path.exists():
        print(f"Error: JSON folder not found: {json_path}")
        return False
    
    if not json_path.is_dir():
        print(f"Error: Path is not a directory: {json_path}")
        return False
    
    # Find all JSON files
    json_files = list(json_path.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {json_path}")
        return False
    
    print(f"Found {len(json_files)} JSON files")
    
    all_events = []
    
    # Process each JSON file
    for json_file in sorted(json_files):
        print(f"Processing {json_file.name}...")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Handle both single event and list of events
            if isinstance(data, list):
                events = data
            elif isinstance(data, dict):
                events = [data]
            else:
                print(f"  Skipping {json_file.name}: Invalid JSON structure")
                continue
            
            # Process each event
            for event in events:
                if not isinstance(event, dict):
                    continue
                
                # Ensure is_free field exists (default to False if missing)
                if 'is_free' not in event:
                    # Infer from price_display_teaser or price if available
                    price_teaser = event.get('price_display_teaser', '').lower()
                    price = event.get('price', None)
                    if 'free' in price_teaser or (price is not None and price == 0.0):
                        event['is_free'] = True
                    else:
                        event['is_free'] = False
                
                # Normalize images to proper JSON format
                images = event.get('images', [])
                event['images'] = normalize_images_format(images)
                
                # Build single images column: JSON array string
                event['images'] = json.dumps(event['images'], ensure_ascii=False)
                
                # Flatten the event data
                flattened = flatten_dict(event)
                
                # Normalize any path fields in flattened data
                for key, value in flattened.items():
                    if isinstance(value, str) and ('path' in key.lower() or 'file' in key.lower()):
                        flattened[key] = normalize_path(value)
                
                # Add source file information
                flattened['source_file'] = json_file.name
                
                all_events.append(flattened)
                
        except Exception as e:
            print(f"  Error processing {json_file.name}: {e}")
            continue
    
    if not all_events:
        print("No valid events found in any JSON files")
        return False
    
    print(f"Total events processed: {len(all_events)}")
    
    # Create DataFrame and save to CSV
    try:
        df = pd.DataFrame(all_events)
        
        # Define preferred column order (is_free near price fields)
        # Get all columns that exist in the DataFrame
        all_columns = list(df.columns)
        
        # Define priority columns in desired order
        priority_columns = [
            'title', 'organiser', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
            'price_display_teaser', 'is_free', 'price_display', 'price', 'min_price', 'max_price',
            'age_group_display', 'min_age', 'max_age',
            'datetime_display_teaser', 'datetime_display', 'start_datetime', 'end_datetime',
            'venue_name', 'address_display', 'planning_area', 'region',
            'label', 'keyword_tag', 'categories', 'images', 'id', 'longitude', 'latitude', 'checked'
        ]
        
        # Build ordered column list: priority columns first, then any remaining columns
        ordered_columns = []
        for col in priority_columns:
            if col in all_columns:
                ordered_columns.append(col)
        
        # Add any remaining columns that weren't in priority list
        for col in all_columns:
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        # Reorder DataFrame columns
        df = df[ordered_columns]
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        
        print(f"✅ CSV file created successfully: {output_path}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        
        # Show column names
        print(f"\nColumns in CSV:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        return True
        
    except Exception as e:
        print(f"Error creating CSV file: {e}")
        return False


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) == 3:
        json_folder = sys.argv[1]
        output_csv = sys.argv[2]
    else:
        print("Usage: python json_to_csv.py [json_folder] [output_csv]")
        print("\nExamples:")
        print("  python json_to_csv.py data/events_output/mall_add mall_add_events.csv")
        print("  python json_to_csv.py data/events_output/20251001_000000 events_20251001.csv")
        print("  python json_to_csv.py data/events_output/attraction_add attractions.csv")
        sys.exit(1)
    
    print("Converting JSON files to CSV...")
    success = process_json_files(json_folder, output_csv)
    
    if success:
        print("\n✅ Conversion completed successfully!")
    else:
        print("\n❌ Conversion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
