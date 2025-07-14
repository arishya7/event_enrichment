import requests

from src.utils.config import config    

def googlePlace_searchText(query:str):
    
    headers = {
      "X-Goog-Api-Key": config.google_api_key,
      "Content-Type": "application/json",
      "X-Goog-FieldMask": "places.formattedAddress,places.location"
    }

    body = {
        "textQuery": query,
        "regionCode": "SG",
        "languageCode": "en"
    }

    response = requests.post(
            url = config.googlePlace.searchTextURL, 
            headers=headers,
            json=body
            )
    

    response.raise_for_status()
    result = response.json()

    if not result.get('places'):
        return None
    
    return result['places'][0]

def get_coordinates_from_address(address):
    """Get longitude and latitude from address using Google Places API.
    
    Args:
        address (str): Full address to geocode
        
    Returns:
        tuple: (longitude, latitude) or (None, None) if lookup fails
    """
    if not address or not address.strip():
        return None, None
    
    try:
        place_data = googlePlace_searchText(address.strip())
        if place_data and 'location' in place_data:
            location = place_data['location']
            longitude = location.get('longitude')
            latitude = location.get('latitude')
            return longitude, latitude
    except Exception as e:
        print(f"Error getting coordinates for address '{address}': {str(e)}")
    
    return None, None