from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path
import shutil
import os

from src.core import *
from src.services.custom_search import *
from src.services.places import *
from src.utils.file_utils import *
from src.utils.config import config

@dataclass
class Event:
    """Class representing an event with all its details.
    
    Attributes:
        title (str): Event title
        blurb (str): Short description or summary
        description (str): Full event description
        guid (str): Globally unique identifier
        url (str): Event webpage URL
        price_display (str): Formatted price string for display
        price (float): Numeric price value
        is_free (bool): Whether the event is free
        organiser (str): Event organizer name
        age_group_display (str): Formatted age range for display
        min_age (float): Minimum age requirement
        max_age (float): Maximum age limit
        datetime_display (str): Formatted date/time for display
        start_datetime (str): Event start date and time
        end_datetime (str): Event end date and time
        venue_name (str): Name of the venue
        categories (List[str]): Event categories/tags
        scraped_on (str): Timestamp when event was scraped
        full_address (str): Complete venue address
        latitude (float): Venue latitude
        longitude (float): Venue longitude
        images (List[Dict[str, str]]): List of image dictionaries with keys:
            - local_path: Local filesystem path where the image is stored
            - original_url: Original URL where the image was downloaded from
            - filename: Name of the image file
            - source_credit: Attribution or credit for the image source
    """
    title: str
    blurb: str
    description: str
    guid: str
    activity_or_event: str
    url: str
    price_display: str
    price: float
    is_free: bool
    organiser: str
    age_group_display: str
    min_age: float
    max_age: float
    datetime_display: str
    start_datetime: str
    end_datetime: str
    venue_name: str
    categories: List[str]
    scraped_on: str
    # Optional fields with defaults
    full_address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    images: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, event_dict: Dict[str, str]) -> 'Event':
        """Creates an Event instance from a dictionary.
        
        Args:
            event_dict (Dict[str, str]): Dictionary containing event data
            
        Returns:
            Event: New Event instance with data from dictionary
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Convert string values to appropriate types
            price = float(event_dict.get('price', 0.0))
            min_age = float(event_dict.get('min_age', 0.0))
            max_age = float(event_dict.get('max_age', 0.0))
            latitude = float(event_dict.get('latitude', 0.0))
            longitude = float(event_dict.get('longitude', 0.0))
            
            # Convert string list to actual list if needed
            categories = event_dict.get('categories', [])
            if isinstance(categories, str):
                categories = categories.split(',')
                
            # Get images list - no conversion needed since it's already a list of dicts
            images = event_dict.get('images', [])
                
            return cls(
                title=event_dict['title'],
                blurb=event_dict['blurb'],
                description=event_dict['description'],
                guid=event_dict['guid'],
                activity_or_event=event_dict['activity_or_event'],
                url=event_dict['url'],
                price_display=event_dict['price_display'],
                price=price,
                is_free=event_dict.get('is_free', False),
                organiser=event_dict['organiser'],
                age_group_display=event_dict['age_group_display'],
                min_age=min_age,
                max_age=max_age,
                datetime_display=event_dict['datetime_display'],
                start_datetime=event_dict['start_datetime'],
                end_datetime=event_dict['end_datetime'],
                venue_name=event_dict['venue_name'],
                categories=categories,
                scraped_on=event_dict.get('scraped_on', datetime.now().isoformat()),
                full_address=event_dict.get('full_address', ''),
                latitude=latitude,
                longitude=longitude,
                images=images
            )
        except KeyError as e:
            print(f"[ERROR][Event.from_dict] Missing required field in event data: {str(e)}")
            raise
        except ValueError as e:
            print(f"[ERROR][Event.from_dict] Invalid value in event data: {str(e)}")
            raise
        except Exception as e:
            print(f"[ERROR][Event.from_dict] Failed to create event from dictionary: {str(e)}")
            raise
    
    def get_address_n_coord(self) -> tuple[str, float, float]:
        """Get the full address and coordinates for the event venue.
        
        Returns:
            tuple[str, float, float]: Tuple containing (full_address, latitude, longitude)
        """
        place = googlePlace_searchText(self.venue_name)
        if place:
            return (place['formattedAddress'], place['location']['latitude'], place['location']['longitude'])
        else:
            return None


    def get_images(self, output_dir: Optional[Path] = None) -> List[Dict[str, str]]:
        """Get images related to the event.
        
        Args:
            output_dir (Optional[Path]): Directory to save downloaded images. 
                                       If None, images won't be downloaded.
        
        Returns:
            List[Dict[str, str]]: List of image dictionaries with keys:
                - local_path: Local filesystem path where the image is stored
                - original_url: Original URL where the image was downloaded from
                - filename: Name of the image file
                - source_credit: Attribution or credit for the image source
        """
        # Create search query from event details
        search_query = f"{self.title} by {self.organiser}"
        
        # Search for images
        image_urls = search_images(
            query=search_query,
            site_to_search=self.url
        )
        
        if not image_urls or not output_dir:
            return []

        # Download images and collect metadata
        downloaded_images = []
        for idx, url in enumerate(image_urls,1):
            # Create unique filename based on event GUID and image index
            filename_without_ext = f"{re.sub(r'[^a-zA-Z0-9]', '_', self.title)}_{idx}"
            image_path = output_dir / filename_without_ext
            result = download_image(url, image_path)
            if result:
                downloaded_images+=[result]

        return downloaded_images

if __name__ == "__main__":
    print("\n=== Testing Event Class ===\n")
    
    # Create a test event
    test_event = Event(
        title="Test Family Fun Day",
        blurb="A fun day for the whole family",
        description="Join us for a day of activities, games, and food!",
        guid="test123",
        activity_or_event="event",
        url="https://example.com/event",
        price_display="$10",
        price=10.0,
        is_free=False,
        organiser="Fun Events Co",
        age_group_display="All ages",
        min_age=0,
        max_age=99,
        datetime_display="1 July 2025, 10am - 5pm",
        start_datetime="2025-07-01T10:00:00",
        end_datetime="2025-07-01T17:00:00",
        venue_name="Gardens by the Bay",
        categories=["Family", "Activities"],
        scraped_on=datetime.now().isoformat()
    )
    
    # Create temp directory for test
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    print("1. Testing get_address_n_coord:")
    try:
        address, lat, lon = test_event.get_address_n_coord()
        print(f"✓ Success: Got address and coordinates")
        print(f"  Address: {address}")
        print(f"  Coordinates: {lat}, {lon}")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        
    print("\n2. Testing get_images:")
    try:
        images = test_event.get_images(temp_dir)
        print(f"✓ Success: Found {len(images)} images")
        for i, img in enumerate(images, 1):
            print(f"\nImage {i}:")
            print(f"  Local path: {img['local_path']}")
            print(f"  Original URL: {img['original_url']}")
            print(f"  Filename: {img['filename']}")
            if 'source_credit' in img:
                print(f"  Source credit: {img['source_credit']}")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
    
    print("\n=== Test Complete ===")
    
    # Ask user to verify results
    print("\nPlease check if everything looks correct.")
    print("1. Check if the address and coordinates make sense")
    print("2. Check if images were downloaded to the temp folder")
    print("3. Verify image quality and relevance")
    
    while True:
        response = input("\nDid all tests pass correctly? (yes/no): ").lower()
        if response in ['yes', 'no']:
            break
        print("Please answer 'yes' or 'no'")
    
    if response == 'no':
        print("\n❌ Tests failed according to user verification")
        print("Please check the logs above and fix any issues")
    else:
        print("\n✅ All tests passed user verification")
    
    # Cleanup temp directory
    print("\nCleaning up temporary files...")
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print("✓ Successfully deleted temp folder and all its contents")
    except Exception as e:
        print(f"✗ Failed to delete temp folder: {str(e)}")
        print("  You may need to delete it manually")

