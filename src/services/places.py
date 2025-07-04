import requests
import json

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