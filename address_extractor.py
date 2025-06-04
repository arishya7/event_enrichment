import json
from typing import Dict, Any
import requests

def get_address_and_coord(query: str, google_api_key: str)->dict:
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        'X-Goog-Api-Key': google_api_key,
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.formattedAddress,places.location"
    }
    body = {
        "textQuery": query,
        "regionCode": "SG",
        "languageCode": "en"
    }
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    result = response.json()
    if not result.get('places'):
        print(f"Warning: No results found for query: {query}")
        return {"address": None, "latitude": None, "longitude": None}
    
    place = result['places'][0] #Top search result 
    return {
        "address": place['formattedAddress'],
        "latitude": place['location']['latitude'],
        "longitude": place['location']['longitude']
    }

def extract_venue_details(event_dict: dict, google_api_key: str) -> dict:
    address_details = get_address_and_coord(event_dict['venue'], google_api_key)
    event_dict['full_address'] = address_details['address']
    event_dict['latitude'] = address_details['latitude']
    event_dict['longitude'] = address_details['longitude']
    return event_dict

def main():
    return

if __name__ == "__main__":
    main() 