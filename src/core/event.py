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
            address_display (str): Complete venue address (default: "")
            latitude (float): Venue latitude (default: 0.0)
            longitude (float): Venue longitude (default: 0.0)
            images (List[Dict[str, str]]): List of image dictionaries (default: [])
            checked (bool): Whether event has been reviewed (default: False)
            keyword_tag (str): Comma-separated search keywords (default: "")
            min_price (float): Minimum price in SGD (default: 0.0)
            max_price (float): Maximum price in SGD (default: 0.0)
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
    address_display: str = field(default="")
    latitude: float = field(default=0.0)
    longitude: float = field(default=0.0)
    images: List[Dict[str, str]] = field(default_factory=list)
    checked: bool = field(default=False)
    keyword_tag: str = field(default="")  # Comma-separated string
    min_price: float = field(default=0.0)
    max_price: float = field(default=0.0)
    planning_area: str = field(default="")
    region: str = field(default="")
    id: int = 431  # Event ID, assigned later in pipeline
    label_tag: str = ""  # User-editable label for custom annotations
    skip_url_validation: bool = field(default=False, repr=False)  # Skip URL search API calls

    def __post_init__(self):
        """Initialize computed fields after object creation."""
        # Set up is_free variable based on price
        self.is_free = True if self.price == 0.0 else False

        # Set up price display teaser if it has only paid options
        if self.price_display_teaser == "From $":
            self.price_display_teaser += str(int(self.price))
        
        # Skip URL validation if disabled (saves API quota)
        if self.skip_url_validation:
            return
            
        # Skip URL search for events with placeholder/default values to avoid wasting API quota
        is_placeholder_event = (
            self.title == "Untitled Event" or
            self.organiser == "Unknown" or
            not self.title.strip() or
            not self.organiser.strip()
        )
        
        # Check if current URL is valid and try to find a valid one if needed
        # Only search if we have meaningful event data (not placeholder values)
        if not is_placeholder_event and not validate_url(self.url):
            new_url = search_valid_url(
                event_title=self.title,
                organiser=self.organiser
            )
            if new_url:
                self.url = new_url

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
        def _to_float(value, default: float = 0.0) -> float:
            """Convert values to float safely, treating None/'' as default."""
            try:
                if value is None or value == "":
                    return default
                return float(value)
            except (TypeError, ValueError):
                return default

        try:
            # Convert string values to appropriate types
            price = _to_float(event_dict.get('price'), 0.0)
            min_price = _to_float(event_dict.get('min_price'), price)  # Default to price if not specified
            max_price = _to_float(event_dict.get('max_price'), price)  # Default to price if not specified
            min_age = _to_float(event_dict.get('min_age'), 0.0)
            max_age = _to_float(event_dict.get('max_age'), 0.0)
            latitude = _to_float(event_dict.get('latitude'), 0.0)
            longitude = _to_float(event_dict.get('longitude'), 0.0)
            
            # Handle keyword_tag: convert from array to comma-separated string if needed
            keyword_tag = event_dict.get('keyword_tag', '')
            if isinstance(keyword_tag, list):
                keyword_tag = ', '.join(str(k) for k in keyword_tag if k)
            elif not isinstance(keyword_tag, str):
                keyword_tag = str(keyword_tag) if keyword_tag else ''

            # Get required fields with defaults - critical fields must have values
            title = event_dict.get('title', 'Untitled Event')
            description = event_dict.get('description', '')
            guid = event_dict.get('guid', '')
            activity_or_event = event_dict.get('activity_or_event', 'event')
            url = event_dict.get('url', '')
            organiser = event_dict.get('organiser', 'Unknown')
            venue_name = event_dict.get('venue_name', '')
            
            # Handle blurb - use description as fallback if missing
            blurb = event_dict.get('blurb', '')
            if not blurb and description:
                # Use first 60 chars of description as fallback blurb
                blurb = description[:60].strip() + ('...' if len(description) > 60 else '')
            elif not blurb:
                blurb = title[:60] if title else 'No description available'
            
            # Get other required fields with sensible defaults
            price_display_teaser = event_dict.get('price_display_teaser', 'Free')
            price_display = event_dict.get('price_display', 'Free')
            age_group_display = event_dict.get('age_group_display', 'All ages')
            datetime_display_teaser = event_dict.get('datetime_display_teaser', '')
            datetime_display = event_dict.get('datetime_display', '')
            start_datetime = event_dict.get('start_datetime', '1970-01-01T00:00:00+08:00')
            end_datetime = event_dict.get('end_datetime', '9999-12-31T23:59:59+08:00')
            categories = event_dict.get('categories', [])
            if not categories:
                categories = ['Attraction']  # Default category
            
            return cls(
                id=event_dict.get('id', 431),
                label_tag=event_dict.get('label_tag', ''),
                title=title,
                blurb=blurb,
                description=description,
                guid=guid,
                activity_or_event=activity_or_event,
                url=url,
                price_display_teaser=price_display_teaser,
                price_display=price_display,
                price=price,
                organiser=organiser,
                age_group_display=age_group_display,
                min_age=min_age,
                max_age=max_age,
                datetime_display_teaser=datetime_display_teaser,
                datetime_display=datetime_display,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                venue_name=venue_name,
                address_display=event_dict.get('address_display', ''),
                categories=categories,
                scraped_on=event_dict.get('scraped_on', datetime.now().isoformat()),
                latitude=latitude,
                longitude=longitude,
                images=event_dict.get('images', []),
                keyword_tag=keyword_tag,
                min_price=min_price,
                max_price=max_price,
                planning_area=event_dict.get('planning_area', ''),
                region=event_dict.get('region', '')
            )
        except KeyError as e:
            # This should rarely happen now since we use .get() with defaults
            print(f"[ERROR][Event.from_dict] Missing required field in event data: {str(e)}")
            print(f"[ERROR][Event.from_dict] Event data keys: {list(event_dict.keys())}")
            raise
        except ValueError as e:
            print(f"[ERROR][Event.from_dict] Invalid value in event data: {str(e)}")
            raise
        except Exception as e:
            print(f"[ERROR][Event.from_dict] Failed to create event from dictionary: {str(e)}")
            raise
    
    def get_address_n_coord(self) -> Optional[Tuple[str, float, float]]:
        """Get the address and coordinates for the event venue.
        
        Returns:
            Optional[Tuple[str, float, float]]: Tuple containing (address_display, latitude, longitude) 
            or None if no place found
        """
        if not self.venue_name:
            return ('','','')
        place = googlePlace_searchText(self.venue_name)
        if place:
            return (place['formattedAddress'], place['location']['latitude'], place['location']['longitude'])
        else:
            return ('','','')


    def get_images(self, output_dir: Optional[Path] = None) -> List[Dict[str, str]]:
        """Get images related to the event by crawling the event URL.
        
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
        # Extract images directly from the event URL (web crawling)
        image_urls = extract_images(url=self.url, max_images=3)
        
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

