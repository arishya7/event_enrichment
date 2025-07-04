from dataclasses import dataclass, field
import time
from typing import Dict, Optional, Union
from pathlib import Path
import json
from datetime import datetime
import shutil


from src.utils.config import config
from src.core import *
from src.core.database import *
from src.utils.file_utils import *

@dataclass
class Run:
   
    timestamp: str
    blogs: list[Blog] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Initialize directory structure after instance creation."""
        # Directory creation for this run
        self.setup_directories()
        
        for blog_name, blog_feed_url in config.blog_website.__dict__.items():
            self.blogs += [Blog(blog_name, blog_feed_url,self.timestamp)]

    def setup_directories(self) -> None:
        """Create all necessary directories for this run."""
        self.events_output_dir.mkdir(exist_ok=True)
        self.timestamp_dir.mkdir(exist_ok=True)
        self.image_dir.mkdir(exist_ok=True)
        self.feed_dir.mkdir(exist_ok=True)
        self.articles_output_dir.mkdir(exist_ok=True)

    @property
    def events_output_dir(self) -> Path:
        """Base directory for event outputs."""
        return Path(config.paths.events_output)

    @property
    def timestamp_dir(self) -> Path:
        """Directory for this specific run's outputs."""
        return self.events_output_dir / self.timestamp

    @property
    def image_dir(self) -> Path:
        """Directory for storing images."""
        return self.timestamp_dir / "images"

    @property
    def feed_dir(self) -> Path:
        """Directory for temporary feed files."""
        return Path(config.paths.temp_feed)

    @property
    def articles_output_dir(self) -> Path:
        """Directory for temporary article outputs."""
        return Path(config.paths.temp_articles_output)

    def start(self) -> None:
        init_db()

        print("\n" + "="*50)
        print(f"🕒 Run started at: {self.timestamp}")
        print("="*50 + "\n")

        print("📚 Blogs to be processed:")
        print("┌─────────────────────────────────────────")
        for blog_name, blog_feed_url in config.blog_website.__dict__.items():
            print(f"│ • {blog_name:<15} {blog_feed_url}")
        print("└─────────────────────────────────────────")

        for blog in self.blogs:
            # Calculate consistent width for the box
            box_width = 60
            header_text = f"─ Processing: {blog.name.upper()} "
            remaining_dashes = box_width - len(header_text) - 1  # -1 for the ┌
            top_line = f"┌{header_text}" + "─" * remaining_dashes
            bottom_line = "└" + "─" * (box_width - 1)
            
            print(f"\n{top_line}")
            
            # blog.extract_feed() ##Figure this out later in devs
            (blog.articles, articles_json_filepath) = blog.parse_feed_file()
            # Can be inside parse_feed_file()
            if len(blog.articles) > 0:
                print(f"│ ✅ Found {len(blog.articles)} articles")
                if articles_json_filepath:
                    print(f"│ 📁 Saved articles json to: {articles_json_filepath}")
                print("│")
            else:
                print("│ ❌ No new articles found")
                print(bottom_line)
                continue
            
            for idx, article_obj in enumerate(blog.articles,1):
                print(f"│ ┌─ Article {idx}/{len(blog.articles)} " + "─" * (30 - len(str(idx)) - len(str(len(blog.articles)))), flush=True)
                print(f"│ │ [DEBUG] Processing article {idx} at {time.strftime('%H:%M:%S')}", flush=True)
                print(f"│ │ 📰 {article_obj.title}", flush=True)
                print(f"│ │ 🔗 {article_obj.guid}", flush=True)
                print(f"│ │ 🆔 Post ID: {article_obj.post_id}", flush=True)
                print("│ │", flush=True)
                
                article_obj.events = article_obj.extract_events()
                
                if article_obj.events:
                    print(f"│ │ ✨ Found! Number of events: {len(article_obj.events)}")
                    print("│ │")
                    for event_idx, event_obj in enumerate(article_obj.events, 1):
                        print(f"│ │ ┌─ Event {event_idx}/{len(article_obj.events)} " + "─" * (25 - len(str(event_idx)) - len(str(len(article_obj.events)))))
                        print(f"│ │ │ ➤ {event_obj.title}")
                        # Get and set address and coordinates and images
                        add_coord_result = event_obj.get_address_n_coord()
                        if add_coord_result:
                            event_obj.full_address, event_obj.latitude, event_obj.longitude = add_coord_result
                        #Can be inside get add_n_cord
                            print(f"│ │ │ ✅ Address & coordinates extracted")
                        else:
                            print(f"│ │ │ ❌ Address & coordinates not found")
                        event_obj.images = event_obj.get_images(self.image_dir / blog.name)
                        #can be insid eget images
                        print(f"│ │ │ 🖼️  {len(event_obj.images)} images downloaded")
                        print(f"│ │ └" + "─" * 35)
                        print("│ │")
                else:
                    print("│ │ ℹ️  No events found in this article") 
                # Record processing attempt in database
                execute_query(
                "INSERT INTO processed_articles (blog_name, post_id, timestamp, num_events) VALUES (?, ?, ?, ?)",
                (article_obj.blog, article_obj.post_id, article_obj.timestamp, len(article_obj.events))
                )
                print("│ └─────────────────────────────────────────")
            
            events_output_blog_dir = Path(config.paths.events_output) / self.timestamp / f"{blog.name}.json"
            have_loaded_events_as_json = blog.load_events_as_json(events_output_blog_dir)
            
            if have_loaded_events_as_json:
                print(f"│")
                print(f"│ ✅ Events saved to: {events_output_blog_dir}")
            else:
                print(f"│")
                print(f"│ ⚠️  No events found for {blog.name}")
            print(bottom_line)
        
        # Handle review and edit process
        self.handle_events_review()
        
        # Proceed with merge process
        self.merge_events()

        print("\n" + "="*50)
        print("✨ Run completed successfully!")
        print("="*50 + "\n")

    def handle_events_review(self) -> None:
        """Handle the review and edit process for events.
        This includes:
        1. Showing where event files are saved
        2. Getting user confirmation for review/edit
        3. Updating articles after edits
        4. Cleaning up temporary articles_output folder
        """
        print("\n┌─ Final Summary ─────────────────────────")
        print("│ All blogs have been processed.")
        events_dir = Path(config.paths.events_output) / self.timestamp
        json_files = list(events_dir.glob("*.json"))
        
        if json_files:
            print("│ Events are saved in:")
            for json_file in json_files:
                print(f"│ │ {json_file}")
            print("│")
        else:
            print("│ No event JSON files.")
            print("└─────────────────────────────────────────")
            return
        
        confirmation = input("│ Do you want to review and edit the events? (Y/N): ").strip().upper()
        
        if confirmation == 'Y':
            print("│")
            print("│ Launching the web event editor...")
            ## Add the editor here
            input("│ Press Enter when done editing in the browser...")
            # Update articles with edited events
            print("│ Updating articles with edited events...")
            for blog in self.blogs:
                for article in blog.articles:
                    article.update_events()
            print("│ Articles updated successfully.")
        else:
            print("│ Edit operation cancelled.")
        
        # Clean up articles_output folder
        try:
            if self.articles_output_dir.exists():
                print("│")
                print("│ 🧹 Cleaning up temporary articles folder...")
                shutil.rmtree(self.articles_output_dir)
                print(f"│ ✅ Deleted: {self.articles_output_dir}")
            else:
                print("│ ℹ️  Articles output folder already clean.")
        except Exception as e:
            print(f"│ ⚠️  Warning: Could not delete articles folder: {str(e)}")
        
        print("└─────────────────────────────────────────")

    def merge_events(self) -> Optional[Path]:
        """Merge all blog events into a single file and return the filepath.
        Asks for user confirmation before proceeding with the merge.
        
        Returns:
            Optional[Path]: Path to the merged events file, or None if merge was cancelled
        """
        # Check if there are any event files to merge
        timestamp_dir = Path(config.paths.events_output) / self.timestamp
        blog_events_filepath_ls = list(timestamp_dir.glob("*.json"))
        
        if not blog_events_filepath_ls:
            print("\nNo event files found to merge.")
            return 

        merge_confirm = input("\nDo you want to merge the events now? (Y/N): ").strip().upper()
        if merge_confirm != 'Y':
            print("\nMerge operation cancelled.")
            return 

        try:
            total_events = []
            
            # Get the current event index from database
            curr_idx = execute_query(
                "SELECT COALESCE(SUM(num_events), 0) as total FROM processed_articles WHERE timestamp != ?", 
                (self.timestamp,)
            ).fetchone()[0]

            print(f"\nStarting from event index: {curr_idx}")
            
            for blog_event_filepath in blog_events_filepath_ls:
                print(f"Reading {blog_event_filepath.name}...")
                try:
                    with open(blog_event_filepath, 'r', encoding="utf-8") as f:
                        blog_events = json.load(f)
                        
                        # Update event indices
                        for event in blog_events:
                            curr_idx += 1
                            event['event_id'] = curr_idx
                        
                        total_events.extend(blog_events)
                except Exception as e:
                    print(f"Error reading {blog_event_filepath.name}: {str(e)}")
                    continue

            print(f"Total new events merged: {len(total_events)}")

            # Save merged events
            merged_events_filepath = Path('data') / f"events_{self.timestamp}.json"
            with open(merged_events_filepath, 'w', encoding='utf-8') as f:
                json.dump(total_events, f, indent=2, ensure_ascii=False)
            
            print(f"\nMerged events saved in {merged_events_filepath}")
            return merged_events_filepath
            
        except Exception as e:
            print(f"\n[Error] on Run.merge_events(): {str(e)}")
            raise

    def stat(self) -> Dict[str,str]:
        """Get statistics about the current run.
        
        Returns:
            Dict[str, str]]: Dictionary containing run statistics
        """
        print("This is stat function")
        return {}

if __name__ == "__main__":
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run = Run(timestamp)
    run.start()
