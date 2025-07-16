"""
Helper functions for the Event JSON & Image Editor application.
"""

import re
import json
from pathlib import Path
from datetime import datetime, date, time
from typing import List, Dict, Tuple, Optional, Any, Union

from src.ui.constants import EVENTS_OUTPUT_DIR, MAX_IMAGES_PER_EVENT


# Image index management functions
def extract_image_index(filename: str) -> int:
    """Extract index number from filename like 'title_3.jpg' -> 3"""
    if not filename:
        return 9999  # Put non-indexed images at the end
    
    try:
        name_without_ext = Path(filename).stem
        if '_' in name_without_ext:
            potential_index = name_without_ext.split('_')[-1]
            if potential_index.isdigit():
                return int(potential_index)
    except:
        pass
    return 9999  # Put non-indexed images at the end


def get_existing_indexes(images: List[Dict]) -> set:
    """Get set of existing indexes from image filenames"""
    existing_indexes = set()
    for img in images:
        filename = img.get('filename', '')
        if filename:
            index = extract_image_index(filename)
            if index != 9999:  # Only add valid indexes
                existing_indexes.add(index)
    return existing_indexes


def sort_images_by_index(images: List[Dict]) -> None:
    """Sort images array by index number in filename"""
    images.sort(key=lambda img: extract_image_index(img.get('filename', '')))


# File operations
def find_timestamp_folders(base_dir: Union[str, Path]) -> List[Path]:
    """Find all timestamp folders in the base directory"""
    base = Path(base_dir)
    timestamp_folders = []
    for folder in base.glob("*/"):
        if folder.is_dir():
            timestamp_folders.append(folder)
    return sorted(timestamp_folders, reverse=True)  # Sort newest first


def find_json_files_in_timestamp(timestamp_folder: Path) -> List[Path]:
    """Find all JSON files in a specific timestamp folder"""
    json_files = []
    for json_file in timestamp_folder.glob("*.json"):
        json_files.append(json_file)
    return sorted(json_files)


def get_event_images(event_folder: Path, blog_source: str) -> List[Path]:
    """Get event images from a specific folder and blog source"""
    images_dir = event_folder / "images" / blog_source
    if images_dir.exists():
        return list(images_dir.glob("*"))
    return []


def load_events_from_file(file_path: Path) -> List[Dict]:
    """Load events from JSON file"""
    try:
        events = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(events, list):
            raise ValueError("JSON file does not contain a list of events.")
        return events
    except Exception as e:
        raise Exception(f"Failed to load JSON: {e}")


def save_events_to_file(events: List[Dict], file_path: Path) -> None:
    """Save events to JSON file"""
    file_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")


# DateTime handling functions
def parse_iso_datetime(iso_string: str) -> Tuple[Optional[date], Optional[time]]:
    """Parse ISO 8601 datetime string into date and time objects.
    
    Args:
        iso_string (str): ISO 8601 formatted datetime string
        
    Returns:
        tuple: (date_obj, time_obj) or (None, None) if parsing fails
    """
    if not iso_string or not isinstance(iso_string, str):
        return None, None
    
    try:
        # Handle various ISO 8601 formats
        iso_string = iso_string.strip()
        
        # Remove timezone info for parsing (Z or +XX:XX format)
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1]
        elif '+' in iso_string[-6:] or iso_string.count('-') > 2:
            # Remove timezone offset like +08:00 or +0800
            if '+' in iso_string:
                iso_string = iso_string.split('+')[0]
            elif iso_string.count('-') > 2:  # More than 2 dashes means timezone
                parts = iso_string.split('-')
                iso_string = '-'.join(parts[:3]) + 'T' + parts[3].split('T')[1] if 'T' in iso_string else '-'.join(parts[:3])
        
        # Parse the datetime
        if 'T' in iso_string:
            dt = datetime.fromisoformat(iso_string)
        else:
            # If no time component, assume it's just a date
            dt = datetime.strptime(iso_string, '%Y-%m-%d')
        
        return dt.date(), dt.time()
    
    except (ValueError, AttributeError, IndexError):
        # If parsing fails, try to extract just the date
        try:
            date_part = iso_string.split('T')[0] if 'T' in iso_string else iso_string
            dt = datetime.strptime(date_part, '%Y-%m-%d')
            return dt.date(), None
        except:
            return None, None


def combine_to_iso_datetime(date_obj: date, time_obj: time) -> Optional[str]:
    """Combine date and time objects into ISO 8601 string.
    
    Args:
        date_obj (date): Date object
        time_obj (time): Time object
        
    Returns:
        str: ISO 8601 formatted datetime string or None
    """
    if not date_obj:
        return None
    
    if time_obj:
        dt = datetime.combine(date_obj, time_obj)
        return dt.isoformat()
    else:
        # If no time, use midnight
        dt = datetime.combine(date_obj, time.min)
        return dt.isoformat()


# Image display functions
def get_image_display_params(aspect_ratio: str, base_width: int = 1000) -> Dict[str, Any]:
    """Calculate image display parameters based on selected aspect ratio.
    
    Args:
        aspect_ratio (str): Selected aspect ratio ("Original", "4:3", "16:9")
        base_width (int): Base width for image display
        
    Returns:
        dict: Dictionary with CSS style and streamlit parameters
    """
    if aspect_ratio == "4:3":
        # 4:3 aspect ratio
        height = int(base_width * 3 / 4)
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": f"width: {base_width}px; height: {height}px; object-fit: cover;"
        }
    elif aspect_ratio == "16:9":
        # 16:9 aspect ratio  
        height = int(base_width * 9 / 16)
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": f"width: {base_width}px; height: {height}px; object-fit: cover;"
        }
    else:  # Original
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": None
        }


# Event data processing
def generate_image_filename(event: Dict, img_index: int, file_extension: str) -> str:
    """Generate filename for image based on event title and index"""
    event_title = event.get('title', 'untitled_event')
    base_filename = re.sub(r'[^a-zA-Z0-9]', '_', event_title)
    return f"{base_filename}_{img_index}{file_extension}"


def get_next_available_image_index(images: List[Dict]) -> int:
    """Get the next available image index"""
    existing_indexes = get_existing_indexes(images)
    img_index = 1
    while img_index in existing_indexes:
        img_index += 1
    return img_index


def create_image_object(local_path: str, filename: str, original_url: str = "", source_credit: str = "User Upload") -> Dict:
    """Create a new image object with standard structure"""
    return {
        "local_path": local_path,
        "filename": filename,
        "original_url": original_url,
        "source_credit": source_credit
    }


def validate_image_count(current_count: int, max_count: int = MAX_IMAGES_PER_EVENT) -> bool:
    """Validate if more images can be added"""
    return current_count < max_count


def calculate_pagination(total_items: int, items_per_page: int, current_page: int) -> Dict[str, int]:
    """Calculate pagination parameters"""
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0
    
    # Ensure current page is valid
    if current_page >= total_pages and total_pages > 0:
        current_page = total_pages - 1
    elif current_page < 0:
        current_page = 0
    
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    return {
        "total_pages": total_pages,
        "current_page": current_page,
        "start_idx": start_idx,
        "end_idx": end_idx
    } 