from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path
import shutil
import re

from src.services import *
from src.utils import *

@dataclass
class Event:
    """Class representing an event with all its details.
    
    This class encapsulates all information about an event including metadata,
    location details, pricing, and associated images.
    
    Args:
        title (str): Event title (required)
        blurb (str): Short description or summary (required)
        description (str): Full event description (required)
        guid (str): Globally unique identifier (required)
        activity_or_event (str): Type of activity or event (required)
        url (str): Event webpage URL (required)
        price_display_teaser (str): Price teaser text (required)
        price_display (str): Formatted price string for display (required)
        price (float): Numeric price value (required)
        organiser (str): Event organizer name (required)
        age_group_display (str): Formatted age range for display (required)
        min_age (float): Minimum age requirement (required)
        max_age (float): Maximum age limit (required)
        datetime_display_teaser (str): Date/time teaser text (required)
        datetime_display (str): Formatted date/time for display (required)
        start_datetime (str): Event start date and time (required)
        end_datetime (str): Event end date and time (required)
        venue_name (str): Name of the venue (required)
        categories (List[str]): Event categories/tags (required)
        scraped_on (str): Timestamp when event was scraped (required)
        
    Attributes:
        Auto-initialized (set in __post_init__):
            is_free (bool): Whether the event is free (calculated from price)
            
        Optional fields with defaults:
            full_address (str): Complete venue address (default: "")
            latitude (float): Venue latitude (default: 0.0)
            longitude (float): Venue longitude (default: 0.0)
            images (List[Dict[str, str]]): List of image dictionaries (default: [])
            checked (bool): Whether event has been reviewed (default: False)
    """
    # Required input fields
    title: str
    blurb: str
    description: str
    guid: str
    activity_or_event: str
    url: str
    price_display_teaser: str
    price_display: str
    price: float
    organiser: str
    age_group_display: str
    min_age: float
    max_age: float
    datetime_display_teaser: str
    datetime_display: str
    start_datetime: str
    end_datetime: str
    venue_name: str
    categories: List[str]
    scraped_on: str
    
    # Auto-initialized fields
    is_free: bool = field(init=False)
    
    # Optional fields with defaults
    full_address: str = field(default="")
    latitude: float = field(default=0.0)
    longitude: float = field(default=0.0)
    images: List[Dict[str, str]] = field(default_factory=list)
    checked: bool = field(default=False)

    def __post_init__(self):
        """Initialize computed fields after object creation."""
        # Check if current URL is valid and try to find a valid one if needed
        if not validate_url(self.url):
            new_url = search_valid_url(
                event_title=self.title,
                organiser=self.organiser
            )
            if new_url:
                self.url = new_url

        # Set up is_free variable based on price
        self.is_free = True if self.price == 0.0 else False

        # Set up price display teaser if it has only paid options
        if self.price_display_teaser == "From $":
            self.price_display_teaser += str(int(self.price))

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

                
            return cls(
                title=event_dict['title'],
                blurb=event_dict['blurb'],
                description=event_dict['description'],
                guid=event_dict['guid'],
                activity_or_event=event_dict['activity_or_event'],
                url=event_dict['url'],
                price_display_teaser=event_dict['price_display_teaser'],
                price_display=event_dict['price_display'],
                price=price,
                organiser=event_dict['organiser'],
                age_group_display=event_dict['age_group_display'],
                min_age=min_age,
                max_age=max_age,
                datetime_display_teaser=event_dict['datetime_display_teaser'],
                datetime_display=event_dict['datetime_display'],
                start_datetime=event_dict['start_datetime'],
                end_datetime=event_dict['end_datetime'],
                venue_name=event_dict['venue_name'],
                categories=event_dict.get('categories', []),
                scraped_on=event_dict.get('scraped_on', datetime.now().isoformat()),
                full_address=event_dict.get('full_address', ''),
                latitude=latitude,
                longitude=longitude,
                images=event_dict.get('images', [])
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
    
    def get_address_n_coord(self) -> Optional[Tuple[str, float, float]]:
        """Get the full address and coordinates for the event venue.
        
        Returns:
            Optional[Tuple[str, float, float]]: Tuple containing (full_address, latitude, longitude) 
            or None if no place found
        """
        place = googlePlace_searchText(self.venue_name)
        if place:
            return (place['formattedAddress'], place['location']['latitude'], place['location']['longitude'])
        else:
            return ('','','')


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

        # Create base filename path without extension or index
        base_filename = f"{re.sub(r'[^a-zA-Z0-9]', '_', self.title)}"
        base_file_path = output_dir / base_filename
        
        # Download all images at once - download_image handles indexing internally
        downloaded_images = download_image(image_urls, base_file_path)
        
        return downloaded_images

if __name__ == "__main__":
    print("\n=== Testing Event Class ===\n")
    
    # Create a test event
    test_event = Event(
        title="Forest Adventure Club Outdoor Holiday Camps",
        blurb="",
        description="",
        guid="",
        activity_or_event="event",
        url="https://www.forestadventureclub.com",
        price_display="",
        price=0.0,
        is_free=False,
        organiser="Forest Adventure Club",
        age_group_display="",
        min_age=0,
        max_age=99,
        datetime_display="",
        start_datetime="",
        end_datetime="",
        venue_name="ple locations",
        categories=["Family", "Activities"],
        scraped_on=datetime.now().isoformat(timespec="seconds")
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

