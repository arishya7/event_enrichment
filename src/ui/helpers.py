"""
Helper Functions for Event JSON & Image Editor Application

This module provides utility functions for data processing, file operations, datetime handling,
image management, and UI helper functions. It contains reusable functions used throughout
the application for common operations.

The functions are organized into several categories:
- Image Index Management: Functions for handling image indexing and sorting
- File Operations: File system operations for events and data
- DateTime Handling: ISO 8601 datetime parsing and formatting
- Image Display: Image display parameter calculations
- Event Data Processing: Event-specific data manipulation
- Search and Filtering: Event search and pagination functions

Key Features:
- Robust datetime parsing with multiple format support
- Image index management with automatic sorting
- File system operations with error handling
- Search functionality with case sensitivity options
- Pagination calculations for large datasets
- Image display parameter calculations

Dependencies:
- pathlib: File path operations
- datetime: Date and time operations
- json: JSON data handling
- re: Regular expressions for text processing
- typing: Type hints and annotations

Example Usage:
    from src.ui.helpers import parse_iso_datetime, calculate_pagination
    
    # Parse datetime string
    date_obj, time_obj = parse_iso_datetime("2024-01-15T14:30:00")
    
    # Calculate pagination
    pagination = calculate_pagination(100, 10, 0)
"""

import re
import json
from pathlib import Path
from datetime import datetime, date, time
from typing import List, Dict, Tuple, Optional, Any, Union

from src.ui.constants import EVENTS_OUTPUT_DIR, MAX_IMAGES_PER_EVENT


# Image Index Management Functions
def extract_image_index(filename: str) -> int:
    """
    Extract index number from filename like 'title_3.jpg' -> 3.
    
    This function parses image filenames to extract numerical indices.
    It handles various filename formats and returns a default value
    for files without explicit indices.
    
    Args:
        filename (str): Image filename to parse
        
    Returns:
        int: Extracted index number, or 9999 for files without index
        
    Example:
        extract_image_index("event_3.jpg")  # Returns: 3
        extract_image_index("image.jpg")    # Returns: 9999
    """
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
    """
    Get set of existing indexes from image filenames.
    
    Extracts all valid numerical indices from a list of image objects.
    This is useful for determining available index numbers when adding
    new images to an event.
    
    Args:
        images (List[Dict]): List of image dictionaries with 'filename' keys
        
    Returns:
        set: Set of existing index numbers
        
    Example:
        images = [{'filename': 'event_1.jpg'}, {'filename': 'event_3.jpg'}]
        get_existing_indexes(images)  # Returns: {1, 3}
    """
    existing_indexes = set()
    for img in images:
        filename = img.get('filename', '')
        if filename:
            index = extract_image_index(filename)
            if index != 9999:  # Only add valid indexes
                existing_indexes.add(index)
    return existing_indexes


def sort_images_by_index(images: List[Dict]) -> None:
    """
    Sort images array by index number in filename.
    
    Modifies the images list in-place to sort by the numerical index
    extracted from filenames. Images without indices are placed at the end.
    
    Args:
        images (List[Dict]): List of image dictionaries to sort
        
    Example:
        images = [{'filename': 'event_3.jpg'}, {'filename': 'event_1.jpg'}]
        sort_images_by_index(images)
        # Result: [{'filename': 'event_1.jpg'}, {'filename': 'event_3.jpg'}]
    """
    images.sort(key=lambda img: extract_image_index(img.get('filename', '')))


# File Operations
def find_timestamp_folders(base_dir: Union[str, Path]) -> List[Path]:
    """
    Find all timestamp folders in the base directory.
    
    Scans the base directory for subdirectories that represent timestamp
    folders (typically containing event data). Returns a sorted list
    with newest folders first.
    
    Args:
        base_dir (Union[str, Path]): Base directory to search
        
    Returns:
        List[Path]: List of timestamp folder paths, sorted newest first
        
    Example:
        folders = find_timestamp_folders("data/events_output")
        # Returns: [Path("2024-01-15_143000"), Path("2024-01-14_120000")]
    """
    base = Path(base_dir)
    timestamp_folders = []
    for folder in base.glob("*/"):
        if folder.is_dir():
            timestamp_folders.append(folder)
    return sorted(timestamp_folders, reverse=True)  # Sort newest first


def find_json_files_in_timestamp(timestamp_folder: Path) -> List[Path]:
    """
    Find all JSON files in a specific timestamp folder.
    
    Scans a timestamp folder for JSON files containing event data.
    Checks the root folder, 'relevant' subfolder, and 'non-relevant' subfolder.
    Returns a sorted list of JSON file paths.
    
    Args:
        timestamp_folder (Path): Path to timestamp folder
        
    Returns:
        List[Path]: List of JSON file paths in the folder
        
    Example:
        json_files = find_json_files_in_timestamp(Path("data/events_output/2024-01-15"))
        # Returns: [Path("relevant/blog1.json"), Path("non-relevant/blog1.json")]
    """
    json_files = []
    # Check root folder first
    for json_file in timestamp_folder.glob("*.json"):
        json_files.append(json_file)
    # Check 'relevant' subfolder (where relevant JSONs are saved)
    relevant_folder = timestamp_folder / "relevant"
    if relevant_folder.exists() and relevant_folder.is_dir():
        for json_file in relevant_folder.glob("*.json"):
            json_files.append(json_file)
    # Check 'non-relevant' subfolder (where non-relevant JSONs are saved)
    nonrelevant_folder = timestamp_folder / "non-relevant"
    if nonrelevant_folder.exists() and nonrelevant_folder.is_dir():
        for json_file in nonrelevant_folder.glob("*.json"):
            json_files.append(json_file)
    # Sort with relevant files first, then non-relevant, then root folder files
    def sort_key(p: Path) -> tuple:
        if p.parent.name == 'relevant':
            return (0, p.name)
        elif p.parent.name == 'non-relevant':
            return (1, p.name)
        else:
            return (2, p.name)
    return sorted(json_files, key=sort_key)


def get_event_images(event_folder: Path, blog_source: str) -> List[Path]:
    """
    Get event images from a specific folder and blog source.
    
    Looks for images in the event folder structure under the specified
    blog source directory. Returns a list of image file paths.
    
    Args:
        event_folder (Path): Path to event folder
        blog_source (str): Blog source name (e.g., "blog1", "blog2")
        
    Returns:
        List[Path]: List of image file paths
        
    Example:
        images = get_event_images(Path("data/events_output/event1"), "blog1")
        # Returns: [Path("image1.jpg"), Path("image2.png")]
    """
    images_dir = event_folder / "images" / blog_source
    if images_dir.exists():
        return list(images_dir.glob("*"))
    return []


def load_events_from_file(file_path: Path) -> List[Dict]:
    """
    Load events from JSON file.
    
    Reads and parses a JSON file containing event data. Validates that
    the file contains a list of events and handles encoding issues.
    Also normalizes keyword_tag from array to comma-separated string.
    
    Args:
        file_path (Path): Path to JSON file containing events
        
    Returns:
        List[Dict]: List of event dictionaries with normalized keyword_tag
        
    Raises:
        ValueError: If JSON file doesn't contain a list of events
        Exception: For other file reading or parsing errors
        
    Example:
        events = load_events_from_file(Path("data/events_output/events.json"))
        # Returns: [{'title': 'Event 1', ...}, {'title': 'Event 2', ...}]
    """
    try:
        events = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(events, list):
            raise ValueError("JSON file does not contain a list of events.")
        
        # Normalize keyword_tag: convert from array to comma-separated string
        for event in events:
            if 'keyword_tag' in event:
                keyword_tag = event['keyword_tag']
                if isinstance(keyword_tag, list):
                    event['keyword_tag'] = ', '.join(str(k) for k in keyword_tag if k)
                elif not isinstance(keyword_tag, str):
                    event['keyword_tag'] = str(keyword_tag) if keyword_tag else ''
        
        return events
    except Exception as e:
        raise Exception(f"Failed to load JSON: {e}")


def save_events_to_file(events: List[Dict], file_path: Path) -> None:
    """
    Save events to JSON file.
    
    Writes a list of event dictionaries to a JSON file with proper
    formatting and UTF-8 encoding. Also normalizes keyword_tag to ensure
    it's saved as a comma-separated string, not an array.
    
    Args:
        events (List[Dict]): List of event dictionaries to save
        file_path (Path): Path to output JSON file
        
    Example:
        events = [{'title': 'Event 1'}, {'title': 'Event 2'}]
        save_events_to_file(events, Path("output/events.json"))
    """
    # Normalize keyword_tag before saving to ensure it's always a string
    for event in events:
        if 'keyword_tag' in event:
            keyword_tag = event['keyword_tag']
            if isinstance(keyword_tag, list):
                event['keyword_tag'] = ', '.join(str(k) for k in keyword_tag if k)
            elif not isinstance(keyword_tag, str):
                event['keyword_tag'] = str(keyword_tag) if keyword_tag else ''
    
    file_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")


# DateTime Handling Functions
def parse_iso_datetime(iso_string: str) -> Tuple[Optional[date], Optional[time]]:
    """
    Parse ISO 8601 datetime string into date and time objects.
    
    Handles various ISO 8601 datetime formats including:
    - Full datetime: "2024-01-15T14:30:00"
    - Date only: "2024-01-15"
    - With timezone: "2024-01-15T14:30:00Z"
    - With timezone offset: "2024-01-15T14:30:00+08:00"
    
    The function is robust and handles edge cases like:
    - Missing time components
    - Timezone information
    - Invalid or malformed strings
    - Empty or None inputs
    
    Args:
        iso_string (str): ISO 8601 formatted datetime string
        
    Returns:
        tuple: (date_obj, time_obj) or (None, None) if parsing fails
        
    Example:
        parse_iso_datetime("2024-01-15T14:30:00")
        # Returns: (date(2024, 1, 15), time(14, 30, 0))
        
        parse_iso_datetime("2024-01-15")
        # Returns: (date(2024, 1, 15), None)
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
    """
    Combine date and time objects into ISO 8601 string.
    
    Creates a properly formatted ISO 8601 datetime string from separate
    date and time objects. If no time is provided, defaults to midnight.
    
    Args:
        date_obj (date): Date object
        time_obj (time): Time object (can be None)
        
    Returns:
        str: ISO 8601 formatted datetime string or None
        
    Example:
        combine_to_iso_datetime(date(2024, 1, 15), time(14, 30, 0))
        # Returns: "2024-01-15T14:30:00"
        
        combine_to_iso_datetime(date(2024, 1, 15), None)
        # Returns: "2024-01-15T00:00:00"
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


# Image Display Functions
def get_image_display_params(aspect_ratio: str, base_width: int = 1000) -> Dict[str, Any]:
    """
    Calculate image display parameters based on selected aspect ratio.
    
    Generates display parameters for images based on the selected aspect ratio.
    Supports "Original", "4:3", and "16:9" ratios with appropriate CSS styling
    for consistent display across the application.
    
    Args:
        aspect_ratio (str): Selected aspect ratio ("Original", "4:3", "16:9")
        base_width (int): Base width for image display calculations
        
    Returns:
        dict: Dictionary with CSS style and streamlit parameters containing:
            - width: Image width in pixels
            - use_container_width: Whether to use container width
            - css_style: CSS styling for aspect ratio control
            
    Example:
        params = get_image_display_params("16:9", 1000)
        # Returns: {
        #     'width': 1000,
        #     'use_container_width': False,
        #     'css_style': 'width: 1000px; height: 562px; object-fit: cover;'
        # }
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


# Event Data Processing
def generate_image_filename(event: Dict, img_index: int, file_extension: str) -> str:
    """
    Generate filename for image based on event title and index.
    
    Creates a standardized filename for uploaded images using the event title
    and a numerical index. Sanitizes the title to create a valid filename.
    
    Args:
        event (Dict): Event dictionary containing title
        img_index (int): Numerical index for the image
        file_extension (str): File extension (e.g., ".jpg", ".png")
        
    Returns:
        str: Generated filename
        
    Example:
        event = {'title': 'Kids Art Workshop'}
        filename = generate_image_filename(event, 1, '.jpg')
        # Returns: "Kids_Art_Workshop_1.jpg"
    """
    event_title = event.get('title', 'untitled_event')
    base_filename = re.sub(r'[^a-zA-Z0-9]', '_', event_title)
    return f"{base_filename}_{img_index}{file_extension}"


def get_next_available_image_index(images: List[Dict]) -> int:
    """
    Get the next available image index.
    
    Finds the next available numerical index for a new image by checking
    existing image filenames and finding the first unused number.
    
    Args:
        images (List[Dict]): List of existing image dictionaries
        
    Returns:
        int: Next available index number
        
    Example:
        images = [{'filename': 'event_1.jpg'}, {'filename': 'event_3.jpg'}]
        next_index = get_next_available_image_index(images)
        # Returns: 2
    """
    existing_indexes = get_existing_indexes(images)
    img_index = 1
    while img_index in existing_indexes:
        img_index += 1
    return img_index


def create_image_object(local_path: str, filename: str, original_url: str = "", source_credit: str = "User Upload") -> Dict:
    """
    Create a new image object with standard structure.
    
    Creates a standardized image object dictionary with all required fields
    for consistent image data handling throughout the application.
    
    Args:
        local_path (str): Path to the image file on local system
        filename (str): Name of the image file
        original_url (str): Original URL where image was found (optional)
        source_credit (str): Credit/source information for the image
        
    Returns:
        dict: Standardized image object with all required fields
        
    Example:
        img_obj = create_image_object(
            "data/images/event1.jpg",
            "event1.jpg",
            "https://example.com/image.jpg",
            "User Upload"
        )
        # Returns: {
        #     'local_path': 'data/images/event1.jpg',
        #     'filename': 'event1.jpg',
        #     'original_url': 'https://example.com/image.jpg',
        #     'source_credit': 'User Upload'
        # }
    """
    return {
        "local_path": local_path,
        "filename": filename,
        "original_url": original_url,
        "source_credit": source_credit
    }


def validate_image_count(current_count: int, max_count: int = MAX_IMAGES_PER_EVENT) -> bool:
    """
    Validate if more images can be added.
    
    Checks if the current number of images is below the maximum allowed
    to determine if more images can be added to an event.
    
    Args:
        current_count (int): Current number of images
        max_count (int): Maximum allowed images (default from constants)
        
    Returns:
        bool: True if more images can be added, False otherwise
        
    Example:
        can_add = validate_image_count(5, 10)  # Returns: True
        can_add = validate_image_count(10, 10)  # Returns: False
    """
    return current_count < max_count


def calculate_pagination(total_items: int, items_per_page: int, current_page: int) -> Dict[str, int]:
    """
    Calculate pagination information.
    
    Computes pagination parameters for displaying large datasets across
    multiple pages. Handles edge cases like empty datasets and invalid
    page numbers.
    
    Args:
        total_items (int): Total number of items to paginate
        items_per_page (int): Number of items per page
        current_page (int): Current page number (0-based)
        
    Returns:
        dict: Pagination information containing:
            - total_pages: Total number of pages
            - current_page: Current page number (adjusted if invalid)
            - start_idx: Starting index for current page
            - end_idx: Ending index for current page
            - total_items: Total number of items
            
    Example:
        pagination = calculate_pagination(100, 10, 0)
        # Returns: {
        #     'total_pages': 10,
        #     'current_page': 0,
        #     'start_idx': 0,
        #     'end_idx': 10,
        #     'total_items': 100
        # }
    """
    total_pages = (total_items + items_per_page - 1) // items_per_page
    current_page = max(0, min(current_page, total_pages - 1)) if total_pages > 0 else 0
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    return {
        "total_pages": total_pages,
        "current_page": current_page,
        "start_idx": start_idx,
        "end_idx": end_idx,
        "total_items": total_items
    }


def search_events_by_title(events: List[Dict], search_term: str, case_sensitive: bool = False) -> List[Tuple[int, Dict]]:
    """
    Search events by title and return matching events with their indices.
    
    Performs a text search on event titles and returns both the matching
    events and their original indices for proper handling in the UI.
    
    Args:
        events (List[Dict]): List of event dictionaries
        search_term (str): Search term to look for in event titles
        case_sensitive (bool): Whether the search should be case sensitive
        
    Returns:
        List[Tuple[int, Dict]]: List of tuples containing (event_index, event_dict) for matching events
        
    Example:
        events = [
            {'title': 'Art Workshop'},
            {'title': 'Music Concert'},
            {'title': 'Art Exhibition'}
        ]
        results = search_events_by_title(events, 'art', case_sensitive=False)
        # Returns: [(0, {'title': 'Art Workshop'}), (2, {'title': 'Art Exhibition'})]
    """
    if not search_term.strip():
        return []
    
    matching_events = []
    search_term_clean = search_term.strip()
    
    if not case_sensitive:
        search_term_clean = search_term_clean.lower()
    
    for idx, event in enumerate(events):
        title = event.get('title', '')
        if not title:
            continue
            
        title_to_check = title if case_sensitive else title.lower()
        
        # Check if search term is in the title
        if search_term_clean in title_to_check:
            matching_events.append((idx, event))
    
    return matching_events


def filter_events_by_search(events: List[Dict], search_term: str, case_sensitive: bool = False) -> List[Dict]:
    """
    Filter events by search term and return only matching events.
    
    Filters a list of events based on a search term applied to event titles.
    Returns only the events that match the search criteria, maintaining
    the original order of matching events.
    
    Args:
        events (List[Dict]): List of event dictionaries
        search_term (str): Search term to look for in event titles
        case_sensitive (bool): Whether the search should be case sensitive
        
    Returns:
        List[Dict]: List of events that match the search criteria
        
    Example:
        events = [
            {'title': 'Art Workshop'},
            {'title': 'Music Concert'},
            {'title': 'Art Exhibition'}
        ]
        filtered = filter_events_by_search(events, 'art', case_sensitive=False)
        # Returns: [{'title': 'Art Workshop'}, {'title': 'Art Exhibition'}]
    """
    if not search_term.strip():
        return events  # Return all events if search term is empty
    
    matching_indices = [idx for idx, _ in search_events_by_title(events, search_term, case_sensitive)]
    return [events[idx] for idx in matching_indices] 