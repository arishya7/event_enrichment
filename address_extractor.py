import json
import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AddressExtractor:
    def __init__(self, headers: Dict[str, str], body_template: Dict[str, Any]):
        """
        Initialize the AddressExtractor with user-defined headers and body template.
        
        Args:
            headers (Dict[str, str]): User-defined headers for API requests.
                                     Must include necessary headers like 'Content-Type'.
            body_template (Dict[str, Any]): User-defined template for the request body.
                                            The 'textQuery' field will be added by the extractor.
        """
        load_dotenv()
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google Maps API key not found in environment variables")
            
        self.headers = headers
        self.body_template = body_template

    def extract_address_details(self, query: str) -> Dict[str, Any]:
        """
        Extract address details from a venue string using Google Places API Text Search.
        
        Args:
            venue (str): The venue name or partial address
            
        Returns:
            Dict containing address, latitude, and longitude
        """
        try:
            url = f"https://places.googleapis.com/v1/places:searchText"
            
            # Prepare body from user's template, adding the specific query
            api_body = self.body_template.copy()
            api_body["textQuery"] = f"{query}, Singapore" # Assuming Singapore context
            
            api_headers = self.headers.copy()
            api_headers['X-Goog-Api-Key'] = self.api_key
            api_headers["Content-Type"] = "application/json"
            api_headers['X-Goog-FieldMask'] = 'places.formattedAddress,places.location'
            
            response = requests.post(url, headers=api_headers, json=api_body)
            response.raise_for_status() # Raises an exception for HTTP errors
            
            result = response.json()
            
            if not result.get('places'):
                logger.warning(f"No results found for venue: {venue}")
                return {"address": None, "latitude": None, "longitude": None}
            
            place = result['places'][0]
            return {
                "address": place.get('formattedAddress'),
                "latitude": place.get('location', {}).get('latitude'),
                "longitude": place.get('location', {}).get('longitude')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Request error for venue '{venue}': {str(e)}")
        except Exception as e:
            logger.error(f"Error searching venue '{venue}': {str(e)}")
        
        return {"address": None, "latitude": None, "longitude": None}

    def enrich_events_with_address(self, events: list) -> list:
        enriched_events = []
        for event in events:
            if 'venue' not in event or not event['venue']:
                logger.warning(f"No venue found or venue is empty for event: {event.get('title', 'Unknown')}")
                # Add empty fields if you want to keep the event in the list
                event['full_address'] = None
                event['latitude'] = None
                event['longitude'] = None
                enriched_events.append(event)
                continue
                
            venue = event['venue']
            address_details = self.extract_address_details(venue)
            
            event['full_address'] = address_details['address']
            event['latitude'] = address_details['latitude']
            event['longitude'] = address_details['longitude']
            enriched_events.append(event)
            logger.info(f"Processed venue: {venue}")
            
        return enriched_events

def main():
    """Main function to demonstrate usage."""
    try:
        # --- USER: Define your custom headers and body template here ---
        # Example: You MUST provide at least 'Content-Type'.
        custom_headers = {
            'Content-Type': 'application/json',
            # Add any other headers you need, e.g., 'Accept': 'application/json'
        }
        
        # Example: Define the base structure for your searchText request body.
        # The 'textQuery' will be added by the AddressExtractor.
        # You might want to include fields like 'locationBias' or 'languageCode'.
        custom_body_template = {
            "locationBias": {
                "rectangle": { # Bias search towards Singapore
                    "south": 1.2,
                    "west": 103.6,
                    "north": 1.4,
                    "east": 104.0
                }
            },
            # "languageCode": "en", # Optional: specify language
            # Add any other body parameters you need for searchText
        }
        # --- END USER DEFINITION ---
        
        if not custom_headers.get('Content-Type'):
            logger.error("FATAL: 'Content-Type' must be specified in custom_headers.")
            return

        extractor = AddressExtractor(
            headers=custom_headers,
            body_template=custom_body_template
        )
        
        # Ensure events.json exists and is readable
        if not os.path.exists('events.json'):
            logger.error("FATAL: events.json not found. Please create it with your event data.")
            # Create a dummy events.json for a quick test if it doesn't exist
            logger.info("Creating a dummy events.json for testing purposes.")
            dummy_events = [
                {"title": "Test Event 1", "venue": "Gardens by the Bay"},
                {"title": "Test Event 2", "venue": "Singapore Art Museum"},
                {"title": "Invalid Venue Event", "venue": ""} # Test empty venue
            ]
            with open('events.json', 'w', encoding='utf-8') as f:
                json.dump(dummy_events, f, indent=2, ensure_ascii=False)
            events = dummy_events
        else:
            with open('events.json', 'r', encoding='utf-8') as f:
                events = json.load(f)
        
        enriched_events = extractor.enrich_events_with_address(events)
        
        with open('events_with_address.json', 'w', encoding='utf-8') as f:
            json.dump(enriched_events, f, indent=2, ensure_ascii=False)
            
        logger.info("Successfully processed all events. Output in events_with_address.json")
        
    except ValueError as ve:
        logger.error(f"Configuration Error: {str(ve)}")
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        # raise # Optionally re-raise for debugging

if __name__ == "__main__":
    main() 