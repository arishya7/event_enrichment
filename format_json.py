#!/usr/bin/env python3
"""
Format JSON files to ensure proper JSON structure, especially for images.
Converts backslashes to forward slashes and ensures images are in proper format.

Usage: python format_json.py [json_folder]

Example: python format_json.py data/events_output/mall_add
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Union
from html import unescape


def normalize_path(path: Union[str, None]) -> str:
    """
    Normalize file paths to use forward slashes.
    
    Args:
        path: File path to normalize
        
    Returns:
        Normalized path with forward slashes
    """
    if not path or not isinstance(path, str):
        return ""
    return path.replace('\\', '/')


def clean_text_field(text: Union[str, None]) -> str:
    """
    Clean text fields by normalizing special characters and fixing encoding issues.
    
    Fixes:
    - Curly quotes (smart quotes) → straight quotes
    - En/em dashes → regular hyphens
    - HTML entities → decoded text
    - Encoding errors (like Äì) → fixed or removed
    - Control characters → removed
    - Multiple whitespace → single space
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return text if isinstance(text, str) else ""
    
    # Try to fix encoding issues first
    # Remove common encoding corruption patterns like "Äì" (Windows-1252 misread as UTF-8)
    # These patterns often appear when text is incorrectly decoded
    text = re.sub(r'Ä[ìíîï]', '', text)  # "Äì" pattern
    text = re.sub(r'[Ää][ìíîï]', '', text)  # Variations
    
    # Common Windows-1252 characters that appear as garbled UTF-8    encoding_fixes = {
    encoding_fixes = {
        # Existing fixes
        'Ä': '',
        'ä': '',
        'ì': '',
        'í': '',
        'î': '',
        'ï': '',
        'â': '',
        '€': 'EUR',
        '™': 'TM',
        '©': '(c)',
        '®': '(R)',
        '…': '...',
        '–': '-',
        '—': '-',
        '―': '-',

        # Additional variations you requested
        "â€™": "'",
        "â€˜": "'",
        "â€œ": "\"",
        "â€": "\"",
        "â€“": "-",
        "â€”": "-",
        "â€¢": "•",
        "â€¦": "...",
        "Ã©": "é",
        "Ã": "à",     
        "‚Äô": "'",
        "‚Äì": "-",
        "Â": "",      
    }

    
    # Apply encoding fixes
    for bad_char, replacement in encoding_fixes.items():
        text = text.replace(bad_char, replacement)
    
    # Decode HTML entities (in case of double encoding)
    text = unescape(text)
    
    # Normalize quotes: curly quotes to straight quotes
    text = text.replace(''', "'")  # Left single quotation mark
    text = text.replace(''', "'")  # Right single quotation mark
    text = text.replace('"', '"')  # Left double quotation mark
    text = text.replace('"', '"')  # Right double quotation mark
    text = text.replace('‚', ',')  # Single low-9 quotation mark
    text = text.replace('„', '"')  # Double low-9 quotation mark
    text = text.replace('‹', '<')  # Single left-pointing angle quotation mark
    text = text.replace('›', '>')  # Single right-pointing angle quotation mark
    text = text.replace('«', '"')  # Left-pointing double angle quotation mark
    text = text.replace('»', '"')  # Right-pointing double angle quotation mark
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize whitespace: replace tabs and newlines with spaces
    text = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def normalize_images_format(images: List[Any]) -> List[Dict[str, Any]]:
    """
    Ensure all images are in proper JSON format with normalized paths.
    
    Args:
        images: List of image objects or URLs
        
    Returns:
        List of normalized image objects with proper structure
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


def format_json_file(file_path: Path) -> bool:
    """
    Format a single JSON file to ensure proper structure.
    
    Args:
        file_path: Path to JSON file to format
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Load JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print(f"  Skipping {file_path.name}: Not a list of events")
            return False
        
        modified = False
        
        # Process each event
        for event in data:
            if not isinstance(event, dict):
                continue
            
            # Clean text fields (title, blurb, description, datetime_display)
            text_fields = ['title', 'blurb', 'description', 'datetime_display']
            for field in text_fields:
                if field in event and event[field]:
                    original_value = event[field]
                    cleaned_value = clean_text_field(original_value)
                    if cleaned_value != original_value:
                        event[field] = cleaned_value
                        modified = True
            
            # Normalize images
            images = event.get('images', [])
            if images:
                original_images = images
                normalized_images = normalize_images_format(images)
                
                # Check if images were modified
                if json.dumps(original_images, sort_keys=True) != json.dumps(normalized_images, sort_keys=True):
                    event['images'] = normalized_images
                    modified = True
            
            # Normalize any path fields in the event
            path_fields = ['local_path', 'image_path', 'file_path', 'path']
            for field in path_fields:
                if field in event and event[field]:
                    normalized = normalize_path(event[field])
                    if normalized != event[field]:
                        event[field] = normalized
                        modified = True
        
        # Save if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        
        return False
        
    except Exception as e:
        print(f"  Error processing {file_path.name}: {e}")
        return False


def format_json_folder(json_folder_path: str) -> bool:
    """
    Format all JSON files in a folder.
    
    Args:
        json_folder_path: Path to folder containing JSON files
        
    Returns:
        True if successful, False otherwise
    """
    json_path = Path(json_folder_path)
    
    print(f"JSON folder: {json_path}")
    
    if not json_path.exists():
        print(f"Error: Folder not found: {json_path}")
        return False
    
    # Support both a directory and a single file
    if json_path.is_file():
        json_files = [json_path]
    elif json_path.is_dir():
        json_files = sorted(json_path.glob("*.json"))
    else:
        print(f"Error: Path is neither file nor directory: {json_path}")
        return False
    
    if not json_files:
        print(f"No JSON files found in {json_path}")
        return False
    
    print(f"Found {len(json_files)} JSON files")
    
    modified_count = 0
    
    # Process each JSON file
    for json_file in json_files:
        print(f"\nProcessing {json_file.name}...")
        
        if format_json_file(json_file):
            print(f"  ✅ Formatted {json_file.name}")
            modified_count += 1
        else:
            print(f"  ℹ️  No changes needed for {json_file.name}")
    
    print(f"\n✅ Format complete! Modified files: {modified_count}/{len(json_files)}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_json.py [json_folder]")
        print("\nExamples:")
        print("  python format_json.py data/events_output/mall_add")
        print("  python format_json.py data/events_output/20251001_000000")
        print("  python format_json.py data/events_output/attraction_add/alliancefrancaise.json")
        sys.exit(1)
    
    print("Formatting JSON files to ensure proper structure...")
    success = format_json_folder(sys.argv[1])
    
    if success:
        print("\n✅ Formatting completed successfully!")
    else:
        print("\n❌ Formatting failed!")
        sys.exit(1)
