#!/usr/bin/env python3
"""
Download images referenced by JSON files and update each event's images list
with local_path and filename. Uses src.utils.file_utils.download_image.

Usage: python download_missing_images.py [json_folder] [images_folder]

Example:
  python download_missing_images.py data/events_output/mall_add data/events_output/mall_add/images
  python download_missing_images.py data/events_output/20251001_000000 data/events_output/20251001_000000/images
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.file_utils import download_image


def ensure_event_base(images_dir: Path, event_id: str, event_title: str) -> Path:
    """Create a base filename for an event under the images directory.
    Produces names like "601_CausewayPoint" and images become 601_CausewayPoint_1.jpg, etc.
    """
    safe_title = "".join(c for c in (event_title or "").strip() if c.isalnum())
    base_name = f"{event_id}_{safe_title}" if safe_title else str(event_id)
    return images_dir / base_name


def extract_image_urls(images_field: Any) -> List[str]:
    """Extract URL strings from an event's images field, which may be a list of
    dicts with url keys or a list of strings.
    """
    urls: List[str] = []
    if isinstance(images_field, list):
        for item in images_field:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("original_url")
                if isinstance(url, str) and url:
                    urls.append(url)
    return urls


def find_existing_image(image_url: str, images_dir: Path, event_id: str) -> Optional[Dict[str, str]]:
    """Check if an image already exists locally by URL or filename.
    
    Returns existing image metadata if found, None otherwise.
    """
    # First, check if we can find it by looking for files that might match
    # We'll search for files that could be this image
    if not images_dir.exists():
        return None
    
    # Try to find by checking existing JSON entries first (if we have access to them)
    # For now, we'll check if a file with a similar pattern exists
    # This is a simple heuristic - we'll improve it by checking the actual image content
    
    # Check all image files in the directory
    for img_file in images_dir.glob("*"):
        if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            # If filename contains event_id, it might be related
            if event_id in img_file.stem:
                # Return metadata for existing file
                return {
                    "local_path": str(img_file.relative_to(Path("data"))).replace("\\", "/"),
                    "original_url": image_url,
                    "filename": img_file.name,
                    "source_credit": ""  # Will be filled from existing data if available
                }
    
    return None


def merge_image_metadata(existing: List[Dict[str, Any]], downloaded: List[Dict[str, str]], images_dir: Path, event_id: str) -> List[Dict[str, Any]]:
    """Merge downloaded image metadata into existing images list.
    - If existing items are dicts and have local_path/filename, preserve them if file exists
    - If existing items are strings or missing local files, use downloaded results
    - Checks images folder for existing files before overwriting
    """
    if not existing:
        return downloaded

    merged: List[Dict[str, Any]] = []
    for idx, item in enumerate(existing):
        if idx < len(downloaded):
            dl = downloaded[idx]
            
            # Check if existing item already has a local file that exists
            existing_local_path = None
            existing_filename = None
            if isinstance(item, dict):
                existing_local_path = item.get("local_path", "")
                existing_filename = item.get("filename", "")
            
            # Check if the existing file actually exists
            file_exists = False
            if existing_local_path and existing_filename:
                # Try to construct the full path
                if not existing_local_path.startswith("data/"):
                    full_path = images_dir.parent / existing_local_path
                else:
                    full_path = Path("data") / existing_local_path
                
                # Also try just the filename in the images_dir
                filename_path = images_dir / existing_filename
                
                if full_path.exists() and full_path.is_file():
                    file_exists = True
                elif filename_path.exists() and filename_path.is_file():
                    file_exists = True
                    # Update local_path to be relative to data/
                    existing_local_path = str(filename_path.relative_to(Path("data"))).replace("\\", "/")
            
            if isinstance(item, dict):
                updated = dict(item)
                if file_exists:
                    # Keep existing filename and local_path if file exists
                    updated["local_path"] = existing_local_path
                    updated["filename"] = existing_filename
                    # Only update source_credit if not already set
                    if not updated.get("source_credit"):
                        updated["source_credit"] = dl.get("source_credit", "")
                    # Ensure original_url is set
                    updated.setdefault("original_url", item.get("url") or dl.get("original_url"))
                else:
                    # File doesn't exist, use downloaded metadata
                    updated.setdefault("source_credit", dl.get("source_credit"))
                    updated["local_path"] = dl.get("local_path")
                    updated["filename"] = dl.get("filename")
                    updated.setdefault("original_url", item.get("url") or dl.get("original_url"))
                merged.append(updated)
            else:
                # Item is a string, use downloaded result
                merged.append({
                    "original_url": dl.get("original_url"),
                    "local_path": dl.get("local_path"),
                    "filename": dl.get("filename"),
                    "source_credit": dl.get("source_credit"),
                })
        else:
            # No downloaded counterpart; keep as-is if dict, skip if string
            if isinstance(item, dict):
                merged.append(item)
    return merged


def process_json_folder(json_folder_path: str, images_folder_path: str) -> bool:
    json_path = Path(json_folder_path)
    images_path = Path(images_folder_path)

    print(f"JSON folder: {json_path}")
    print(f"Images folder: {images_path}")

    if not json_path.exists():
        print(f"Error: JSON folder not found: {json_path}")
        return False

    images_path.mkdir(parents=True, exist_ok=True)

    total_events_updated = 0
    # Support both a directory (process all *.json) and a single file
    if json_path.is_file():
        json_files = [json_path]
    elif json_path.is_dir():
        json_files = sorted(json_path.glob("*.json"))
    else:
        print(f"Error: Path is neither file nor directory: {json_path}")
        return False

    for json_file in json_files:
        print(f"\nProcessing {json_file.name}...")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                events: List[Dict[str, Any]] = json.load(f)
        except Exception as e:
            print(f"  Failed to read JSON: {e}")
            continue

        file_updated = 0
        for event in events:
            event_id = str(event.get("id", "")).strip()
            if not event_id:
                continue

            images_field = event.get("images", [])
            if not images_field:
                continue

            base_path = ensure_event_base(images_path, event_id, event.get("title", ""))
            
            # Process each image in the field - check which ones need downloading
            urls_to_download = []
            image_status = []  # Track status for each image: 'keep', 'download', or 'skip'
            
            for idx, img_item in enumerate(images_field):
                if isinstance(img_item, dict):
                    # Check if file already exists
                    local_path = img_item.get("local_path", "")
                    filename = img_item.get("filename", "")
                    url = img_item.get("url") or img_item.get("original_url", "")
                    
                    if local_path and filename:
                        # Try multiple path combinations to find the file
                        full_path = None
                        
                        # Path 1: relative to data/
                        if local_path.startswith("data/"):
                            full_path = Path("data") / local_path
                        else:
                            # Path 2: relative to images_path parent
                            full_path = images_path.parent / local_path
                        
                        # Path 3: just the filename in images_dir (check this too)
                        filename_path = images_path / filename
                        
                        # Check which path exists
                        if full_path and full_path.exists() and full_path.is_file():
                            image_status.append(('keep', img_item))
                        elif filename_path.exists() and filename_path.is_file():
                            # File exists but path might be wrong - update it
                            relative_path = str(filename_path.relative_to(Path("data"))).replace("\\", "/")
                            img_item['local_path'] = relative_path
                            img_item['filename'] = filename
                            image_status.append(('keep', img_item))
                        elif url:
                            # File doesn't exist but we have URL - download it
                            urls_to_download.append(url)
                            image_status.append(('download', None))
                        else:
                            # No file, no URL - skip
                            image_status.append(('skip', None))
                    elif url:
                        # Has URL but no local file - needs download
                        urls_to_download.append(url)
                        image_status.append(('download', None))
                    else:
                        # No URL, no file - skip
                        image_status.append(('skip', None))
                elif isinstance(img_item, str):
                    # String URL - needs download
                    urls_to_download.append(img_item)
                    image_status.append(('download', None))
                else:
                    # Unknown format - skip
                    image_status.append(('skip', None))
            
            # Download missing images
            downloaded = []
            if urls_to_download:
                downloaded = download_image(urls_to_download, base_path)
                if downloaded:
                    # Normalize local_path to be relative to data/ (to be consistent with add_image_paths.py)
                    for d in downloaded:
                        if isinstance(d.get("local_path"), str):
                            d["local_path"] = d["local_path"].replace("data\\", "").replace("data/", "")
            
            # Build final images list maintaining order
            updated_images = []
            download_idx = 0
            for status, img_item in image_status:
                if status == 'keep':
                    # Preserve existing image metadata, including filename
                    updated_images.append(img_item)
                elif status == 'download' and download_idx < len(downloaded):
                    # For newly downloaded images, check if we should preserve any existing filename
                    downloaded_img = downloaded[download_idx]
                    
                    # If the original img_item had a filename, check if that file exists
                    # (img_item might be None for string URLs, so check first)
                    if img_item and isinstance(img_item, dict):
                        existing_filename = img_item.get('filename', '')
                        if existing_filename:
                            existing_file_path = images_path / existing_filename
                            if existing_file_path.exists() and existing_file_path.is_file():
                                # Preserve the existing filename and update local_path to match
                                downloaded_img['filename'] = existing_filename
                                # Update local_path to match the existing filename
                                relative_path = str(images_path.relative_to(Path("data"))).replace('\\', '/')
                                downloaded_img['local_path'] = f"{relative_path}/{existing_filename}"
                                # Also preserve other metadata from original if available
                                if img_item.get('source_credit'):
                                    downloaded_img.setdefault('source_credit', img_item.get('source_credit'))
                                if img_item.get('url'):
                                    downloaded_img.setdefault('url', img_item.get('url'))
                                print(f"  Event {event_id}: Preserved existing filename '{existing_filename}' for downloaded image")
                    
                    updated_images.append(downloaded_img)
                    download_idx += 1
                # Skip 'skip' status items
            
            if updated_images:
                event["images"] = updated_images
                file_updated += 1

        if file_updated > 0:
            try:
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(events, f, indent=2, ensure_ascii=False)
                print(f"  Saved {json_file.name} with {file_updated} events updated")
                total_events_updated += file_updated
            except Exception as e:
                print(f"  Failed to write JSON: {e}")

    print(f"\n✅ Download complete! Total events updated: {total_events_updated}")
    return True


if __name__ == "__main__":
    if len(sys.argv) == 3:
        json_folder = sys.argv[1]
        images_folder = sys.argv[2]
    else:
        print("Usage: python download_missing_images.py [json_folder] [images_folder]")
        print("\nExamples:")
        print("  python download_missing_images.py data/events_output/mall_add data/events_output/mall_add/images")
        print("  python download_missing_images.py data/events_output/20251001_000000 data/events_output/20251001_000000/images")
        sys.exit(1)

    print("Downloading images referenced in JSON and updating local paths...")
    process_json_folder(json_folder, images_folder)


