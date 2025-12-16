"""
Services Module for Web Scraping Application

This module provides external service integrations for the web scraping application.
It includes AWS S3 storage, Google Custom Search, Google Generative AI (Gemini),
and Google Places API services.

Services Overview:
- AWS S3: File storage and management for event data and images
- Custom Search: Google Custom Search API for finding event URLs and images
- Generative Language: Google Gemini AI for content generation and processing
- Places: Google Places API for geocoding and location services

Usage:
    from src.services import S3, search_valid_url, gemini_generate_text
    
    # Use S3 for file operations
    s3_client = S3()
    s3_client.upload_file("local_file.json")
    
    # Search for event URLs
    url = search_valid_url("Event Title", "Organiser Name")
    
    # Generate content with Gemini
    response = gemini_generate_text(client, model, prompt, config)
"""

# Import classes and functions individually to avoid circular imports
from .aws_s3 import S3
from .custom_search import search_valid_url, search_images, validate_url
from .generative_language import gemini_generate_text, custom_gemini_generate_content
from .places import googlePlace_searchText, get_coordinates_from_address
from .page_images import extract_images
from .page_emails import extract_company_emails_from_event
try:
    from .places import which_district
except Exception:
    which_district = None

# Define what should be imported with 'from src.services import *'
__all__ = [
    # AWS S3 - Cloud storage service for files and data
    'S3',
    
    # Custom Search - Google Custom Search API for finding URLs and images
    'search_valid_url',
    'search_images', 
    'validate_url',
    
    # Generative Language - Google Gemini AI for content generation
    'gemini_generate_text',
    'custom_gemini_generate_content',
    
    # Places - Google Places API for geocoding and location services
    'googlePlace_searchText',
    'get_coordinates_from_address',
    'which_district',
    
    # Page Images - Extract images directly from webpage URLs
    'extract_images',

    # Page Emails - Extract company emails starting from an event page URL
    'extract_company_emails_from_event'
] 