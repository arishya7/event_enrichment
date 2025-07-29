"""
Constants and configuration for the Event JSON & Image Editor application.
"""

import json
from pathlib import Path

# Load event schema to get available categories
def load_event_schema():
    """Load the event schema from config file."""
    with open("config/event_schema.json", 'r', encoding='utf-8') as f:
        return json.load(f)

# Load schema and extract constants
event_schema = load_event_schema()
AVAILABLE_CATEGORIES = event_schema["items"]["properties"]["categories"]["items"]["enum"]
ACTIVITY_OR_EVENT = event_schema["items"]["properties"]["activity_or_event"]['enum']

# Application constants
MAX_IMAGES_PER_EVENT = 10
DEFAULT_EVENTS_PER_PAGE = 10
DEFAULT_ASPECT_RATIO = "Original"
SUPPORTED_IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]

# File paths
DATA_DIR = Path("data")
EVENTS_OUTPUT_DIR = DATA_DIR / "events_output"
CONFIG_DIR = Path("config")

# UI Configuration
STREAMLIT_PAGE_CONFIG = {
    "page_title": "Event JSON & Image Editor",
    "layout": "wide"
}

# Form field configuration
SPECIAL_FIELDS = [
    'title', 'organiser', 'blurb', 'description', 'url',
    'activity_or_event', 'categories', 'price_display', 'price', 'is_free', 'price_display_teaser',
    'age_group_display', 'min_age', 'max_age', 'datetime_display', 'datetime_display_teaser',
    'start_datetime', 'end_datetime', 'venue_name', 'full_address',
    'latitude', 'longitude', 'checked'
]

DISABLED_FIELDS = ['guid', 'scraped_on', 'latitude', 'longitude']

# Image display parameters
ASPECT_RATIOS = ["Original", "4:3", "16:9"]
IMAGE_DISPLAY_BASE_WIDTH = 1000
THUMBNAIL_PREVIEW_WIDTH = 300 