"""
Google Places API Service for Geocoding and Location Services

This module provides integration with Google Places API for geocoding addresses
and retrieving location information. It includes functions for searching places
by text and extracting coordinates from addresses.

The service is specifically configured for Singapore-based searches with:
- Region code set to "SG" for Singapore
- Language code set to "en" for English
- Focus on formatted addresses and location coordinates
- Error handling for invalid or missing addresses

Features:
- Text-based place search with automatic region filtering
- Address to coordinate conversion (geocoding)
- Automatic error handling and validation
- Singapore-specific search optimization
- Structured response parsing

Dependencies:
- requests: HTTP client for API calls
- src.utils.config: Configuration management

Configuration:
- Requires Google API key for Places API access
- Uses config module for API credentials and endpoints
- Configured for Singapore region (SG) and English language

Example Usage:
    from src.services import googlePlace_searchText, get_coordinates_from_address
    
    # Search for a place by text
    place_data = googlePlace_searchText("Marina Bay Sands")
    
    # Get coordinates from address
    longitude, latitude = get_coordinates_from_address("1 Marina Bay Sands, Singapore")
"""

import requests

from src.utils.config import config    

def googlePlace_searchText(query: str):
    """
    Search for places using Google Places API with text query.
    
    This function searches for places using the Google Places API's text search
    functionality. It's specifically configured for Singapore-based searches with
    automatic region filtering and English language support.
    
    The search is optimized for location discovery by:
    - Using text-based search for flexible query matching
    - Filtering results to Singapore region (SG)
    - Requesting formatted addresses and location coordinates
    - Using English language for consistent results
    
    Args:
        query (str): Text query to search for places (e.g., venue names, addresses)
        
    Returns:
        dict or None: Place data containing formatted address and location coordinates,
                     or None if no places found or error occurs
        
    Raises:
        requests.RequestException: If the API request fails
        KeyError: If the API response doesn't contain expected data
        
    Example:
        place_data = googlePlace_searchText("Singapore Botanic Gardens")
        # Returns: {
        #     'formattedAddress': '1 Cluny Rd, Singapore 259569',
        #     'location': {'latitude': 1.3158, 'longitude': 103.8160}
        # }
    """
    
    # Configure headers for Google Places API
    headers = {
      "X-Goog-Api-Key": config.google_api_key,
      "Content-Type": "application/json",
      "X-Goog-FieldMask": "places.formattedAddress,places.location"  # Request specific fields
    }

    # Configure request body with search parameters
    body = {
        "textQuery": query,
        "regionCode": "SG",  # Focus on Singapore region
        "languageCode": "en"  # Use English language
    }

    # Make API request to Google Places API
    response = requests.post(
            url = config.googlePlace.searchTextURL, 
            headers=headers,
            json=body
            )
    

    response.raise_for_status()
    result = response.json()

    # Check if any places were found in the response
    if not result.get('places'):
        return None
    
    # Return the first (most relevant) place found
    return result['places'][0]

def get_coordinates_from_address(address):
    """
    Get longitude and latitude coordinates from an address using Google Places API.
    
    This function performs geocoding by converting a human-readable address into
    precise geographic coordinates. It uses the Google Places API to search for
    the address and extract the location information.
    
    The function includes comprehensive error handling:
    - Validates input address is not empty
    - Handles API request failures gracefully
    - Returns None coordinates for invalid addresses
    - Provides detailed error logging for debugging
    
    Args:
        address (str): Full address to geocode (e.g., "1 Marina Bay Sands, Singapore")
        
    Returns:
        tuple: (longitude, latitude) coordinates as floats, or (None, None) if lookup fails
        
    Example:
        longitude, latitude = get_coordinates_from_address("1 Marina Bay Sands, Singapore")
        # Returns: (103.8588, 1.2838) or (None, None) if not found
    """
    # Validate input address
    if not address or not address.strip():
        return None, None
    
    try:
        # Search for the address using Google Places API
        place_data = googlePlace_searchText(address.strip())
        
        # Extract coordinates if place data is found
        if place_data and 'location' in place_data:
            location = place_data['location']
            longitude = location.get('longitude')
            latitude = location.get('latitude')
            return longitude, latitude
    except Exception as e:
        print(f"Error getting coordinates for address '{address}': {str(e)}")
    
    # Return None coordinates if lookup fails
    return None, None