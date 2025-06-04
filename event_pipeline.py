import os
from pathlib import Path
from dotenv import load_dotenv
import json
import time

# Import components
from events_extractor import generate, clean_text
from address_extractor import AddressExtractor
from image_extractor import GoogleCustomSearchAPI

class EventPipeline:
    def __init__(self, blog_website: str):
        """Initialize the EventPipeline with configuration."""
        self.blog_website = blog_website
        self.setup_directories()
        self.initialize_components()
        self.results_ls = []
        self.image_mapping = {}

    def setup_directories(self):
        """Create necessary output directories."""
        self.output_dir = Path('events_output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / 'images' / self.blog_website
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def initialize_components(self):
        """Initialize API clients and extractors."""
        try:
            # Initialize address extractor
            self.address_extractor = AddressExtractor(
                headers={'Content-Type': 'application/json'},
                body_template={}
            )
            
            # Initialize image search
            self.image_search = GoogleCustomSearchAPI()
            
            print("All components initialized successfully")
        except ValueError as e:
            print(f"Error initializing components: {e}")
            raise

    def load_articles(self) -> bool:
        """Load articles from JSON file."""
        articles_file = Path(f"articles_output/{self.blog_website}_articles.json")
        if not articles_file.exists():
            print(f"Error: Articles file not found at {articles_file}")
            return False

        try:
            with open(articles_file, 'r', encoding='utf-8') as f:
                self.articles_ls = json.load(f)
            return bool(self.articles_ls)
        except Exception as e:
            print(f"Error loading articles: {e}")
            return False

    def process_single_article(self, article: dict, article_index: int) -> None:
        """Process a single article to extract events."""
        # Create a deep copy and clean content
        article_for_api = json.loads(json.dumps(article))
        if 'content' in article_for_api:
            article_for_api['content'] = clean_text(article_for_api['content'])

        # Generate events
        result_text = generate(json.dumps(article_for_api))
        if not result_text:
            return

        try:
            events = json.loads(result_text)
            if not isinstance(events, list) or not events:
                return

            # Process each event
            for event in events:
                self.enrich_event(event, article.get('url'))

            # Add processed events to results
            self.results_ls.extend(events)
            print(f"Found {len(events)} events in article {article_index}")

        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response from API for article {article_index}: {e}")
            print(f"API Response Text: {result_text[:500]}...")

    def enrich_event(self, event: dict, article_url: str) -> None:
        """Add location and image information to an event."""
        # Add location information
        self.add_location_to_event(event)
        
        # Add images
        self.add_images_to_event(event, article_url)

    def add_location_to_event(self, event: dict) -> None:
        """Add location information to an event."""
        event_title = event.get('title', '')
        event_venue = event.get('venue')
        
        # Initialize location fields
        event['full_address'] = None
        event['latitude'] = None
        event['longitude'] = None
        
        if event_venue:
            search_query = f"{event_title} {event_venue}" if event_title else event_venue
            address_details = self.address_extractor.extract_address_details(search_query)
            event['full_address'] = address_details.get('address')
            event['latitude'] = address_details.get('latitude')
            event['longitude'] = address_details.get('longitude')

    def add_images_to_event(self, event: dict, article_url: str) -> None:
        """Add images to an event."""
        event_title = event.get('title')
        if not event_title:
            return

        image_results = self.image_search.search_images(
            query=event_title,
            num_results=5,
            site_to_search=article_url
        )

        if image_results:
            downloaded_images = self.image_search.download_images(
                image_download_dir=self.images_dir,
                image_results=image_results,
                event_title_for_filename=event_title,
                num_to_download=5
            )
            
            if downloaded_images:
                event['images'] = downloaded_images
                self.image_mapping[event_title] = downloaded_images

    def save_results(self) -> None:
        """Save extracted events and image mapping."""
        if not self.results_ls:
            print("No events found in any articles")
            return

        try:
            # Save events
            events_file = self.output_dir / f"{self.blog_website}_events.json"
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(self.results_ls, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.results_ls)} events to {events_file}")

            # Save image mapping
            mapping_file = self.output_dir / "images" / "image_mapping.json"
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.image_mapping, f, indent=2)
            print("Image mapping saved")
        except Exception as e:
            print(f"Error saving results: {e}")

    def process_articles(self, limit: int = None) -> None:
        """Process all articles to extract events."""
        if not self.load_articles():
            return

        articles_to_process = self.articles_ls[:limit] if limit else self.articles_ls
        print(f"Processing {len(articles_to_process)} articles...")

        for i, article in enumerate(articles_to_process, 1):
            print(f"Processing article {i}/{len(articles_to_process)}")
            self.process_single_article(article, i)
            # Add a small delay between articles to avoid rate limits
            time.sleep(1)

        self.save_results()

def main():
    # Load environment variables
    load_dotenv()
    
    # List of blogs to process
    blogs = ["theasianparent", "sassymamasg"]
    
    for blog in blogs:
        print(f"\nProcessing blog: {blog}")
        try:
            # Initialize and run the event pipeline
            pipeline = EventPipeline(blog)
            pipeline.process_articles(limit=3)  # Process first 3 articles
            print(f"Completed processing for {blog}")
        except Exception as e:
            print(f"Error processing blog {blog}: {e}")
            continue
        
        # Add a delay between processing different blogs
        time.sleep(5)

if __name__ == "__main__":
    main() 