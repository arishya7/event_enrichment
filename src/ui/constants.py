"""
Constants and Configuration for Event JSON & Image Editor Application

This module defines all application constants, configuration settings, and default values
used throughout the UI components. It includes event schema definitions, UI configuration,
file paths, and form field specifications.

"""

import json
from pathlib import Path

def load_event_schema():
    """
    Load the event schema from config file.
    
    Reads the event schema JSON file to extract available categories,
    field definitions, and validation rules for the application.
     Returns:
        dict: Event schema containing field definitions and constraints
        
    Raises:
        FileNotFoundError: If the schema file doesn't exist
        json.JSONDecodeError: If the schema file is invalid JSON
    """
    with open("config/event_schema.json", 'r', encoding='utf-8') as f:
        return json.load(f)

# Load schema and extract constants
event_schema = load_event_schema()

# Event Schema Constants
# Available categories for event classification (from schema)
AVAILABLE_CATEGORIES = event_schema["items"]["properties"]["categories"]["items"]["enum"]

# Activity or event type options (from schema)
ACTIVITY_OR_EVENT = event_schema["items"]["properties"]["activity_or_event"]['enum']

# Application Limits and Constraints
# Maximum number of images allowed per event
MAX_IMAGES_PER_EVENT = 10

# Default number of events to display per page
DEFAULT_EVENTS_PER_PAGE = 10

# Default aspect ratio for image display
DEFAULT_ASPECT_RATIO = "Original"

# Supported image file extensions for upload
SUPPORTED_IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]

# File System Paths
# Base data directory for storing application data
DATA_DIR = Path("data")

# Directory for storing event output files
EVENTS_OUTPUT_DIR = DATA_DIR / "events_output"

# Directory containing configuration files
CONFIG_DIR = Path("config")

# Streamlit UI Configuration
# Page configuration for the main application
STREAMLIT_PAGE_CONFIG = {
    "page_title": "Event JSON & Image Editor",
    "layout": "wide"  # Use wide layout for better space utilization
}

# Form Field Configuration
# List of special fields that have custom rendering logic in the UI
# These fields are handled differently from dynamic fields
SPECIAL_FIELDS = [
    'title', 'organiser', 'blurb', 'description', 'url',
    'activity_or_event', 'categories', 'price_display', 'price', 'is_free', 'price_display_teaser',
    'age_group_display', 'min_age', 'max_age', 'datetime_display', 'datetime_display_teaser',
    'start_datetime', 'end_datetime', 'venue_name', 'full_address',
    'latitude', 'longitude', 'checked'
]

# Fields that should be disabled (read-only) in the UI
# These fields are automatically generated and shouldn't be edited manually
DISABLED_FIELDS = ['guid', 'scraped_on', 'latitude', 'longitude']

# Image Display Configuration
# Available aspect ratios for image display
ASPECT_RATIOS = ["Original", "4:3", "16:9"]

# Base width for image display calculations
IMAGE_DISPLAY_BASE_WIDTH = 1000

# Width for thumbnail preview images
THUMBNAIL_PREVIEW_WIDTH = 300 