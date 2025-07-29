from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import subprocess
import sys

from src.utils import *
from src.core.blog import Blog
from src.core.database import *
from src.services import *

@dataclass
class Run:
    """Main orchestrator class for the web scraping and event extraction process.
    
    This class manages the entire workflow from feed extraction to event processing,
    including database operations, file management, and S3 uploads.
    
    Args:
        timestamp (str): Unique timestamp identifier for this run (required)
        
    Attributes:
        Auto-initialized (set in __post_init__):
            blogs (List[Blog]): List of blog instances to process
            events_output_dir (Path): Base directory for event outputs
            timestamp_dir (Path): Directory for this specific run's outputs
            image_dir (Path): Directory for storing downloaded images
            feed_dir (Path): Directory for temporary feed files
            articles_output_dir (Path): Directory for temporary article outputs
    """
    # Required input fields
    timestamp: str
    
    # Auto-initialized fields (set in __post_init__)
    # blogs: List[Blog] = field(default_factory=list)  # Removed - created in __post_init__
    # events_output_dir: Path = field(init=False)
    # timestamp_dir: Path = field(init=False)
    # image_dir: Path = field(init=False)
    # feed_dir: Path = field(init=False)
    # articles_output_dir: Path = field(init=False)
    
    def __post_init__(self) -> None:
        """Initialize directory structure and blog instances after creation.
        
        Sets up all necessary directories and creates Blog instances for each
        configured blog website.
        """
        # Initialize path properties
        self.events_output_dir = Path(config.paths.events_output)
        self.timestamp_dir = self.events_output_dir / self.timestamp
        self.image_dir = self.timestamp_dir / "images"
        self.feed_dir = Path(config.paths.temp_feed)
        self.articles_output_dir = Path(config.paths.temp_articles_output)
        
        # Create directory structure for this run
        self.setup_directories()
        
        # Initialize blogs list and create blog instances
        self.blogs: List[Blog] = []
        for blog_name, blog_feed_url in config.blog_website.__dict__.items():
            self.blogs.append(Blog(blog_name, blog_feed_url, self.timestamp))

    def setup_directories(self) -> None:
        """Create all necessary directories for this run.
        
        Creates the directory structure needed for storing feeds, articles,
        events, and images during processing.
        """
        # Create directories in order (parent to child)
        self.events_output_dir.mkdir(parents=True, exist_ok=True)  # Create parent first
        self.timestamp_dir.mkdir(exist_ok=True)
        self.image_dir.mkdir(exist_ok=True)
        self.feed_dir.mkdir(parents=True, exist_ok=True)
        self.articles_output_dir.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Execute the complete web scraping and event extraction workflow.
        
        This method orchestrates the entire process:
        1. Initialize database
        2. Extract feeds from blogs
        3. Parse articles and extract events
        4. Handle user review and editing
        5. Merge events into final output
        6. Upload to S3
        7. Record processing results in database
        """
        # Initialize database
        init_db()

        formatter.print_header(f"Run started at: {self.timestamp}")

        # Display blogs to be processed
        formatter.print_section("Blogs to be processed:")
        for blog in self.blogs:
            formatter.print_item(f"{blog.name:<20} {blog.feed_url}")
        formatter.print_section_end()

        # Extract feed from first blog (manual process for now)
        # TODO: Automate this process to handle all blogs automatically
        _ = self.blogs[0].extract_feed()

        # Process each blog
        for blog in self.blogs:
            bottom_line = formatter.print_box_start(blog.name)
            
            # Parse feed and extract articles
            (blog.articles, articles_json_file_path) = blog.parse_feed_file()
            if len(blog.articles) > 0:
                formatter.print_success(f"Found {len(blog.articles)} articles")
                if articles_json_file_path:
                    formatter.print_level1(f"📁 Saved articles json to: {articles_json_file_path}")
                formatter.print_level1("")
            else:
                formatter.print_error("No new articles found")
                formatter.print_box_end(bottom_line)
                continue
            
            # Process each article and extract events
            for idx, article_obj in enumerate(blog.articles, 1):
                formatter.print_article_start(idx, len(blog.articles))
                formatter.print_level2(f"📰 {article_obj.title}")
                formatter.print_level2(f"🔗 {article_obj.guid}")
                formatter.print_level2(f"🆔 Post ID: {article_obj.post_id}")
                formatter.print_level2("")
                formatter.print_level2("Extracting events...")
                
                # Extract events from article using AI
                article_obj.events = article_obj.extract_events()
                
                if article_obj.events:
                    formatter.print_level2(f"✨ Found! Number of events: {len(article_obj.events)}")
                    for event_idx, event_obj in enumerate(article_obj.events, 1):
                        formatter.print_event_start(event_idx, len(article_obj.events))
                        formatter.print_level3(f"➤ {event_obj.title}")
                        
                        # Get address and coordinates for event venue
                        add_coord_result = event_obj.get_address_n_coord()
                        if add_coord_result:
                            event_obj.full_address, event_obj.latitude, event_obj.longitude = add_coord_result
                            formatter.print_success(f"Address & coordinates extracted: {event_obj.full_address}", level=3)
                        else:
                            formatter.print_error("Address & coordinates not found", level=3)
                        
                        # Download images for the event
                        event_obj.images = event_obj.get_images(self.image_dir / blog.name)
                        formatter.print_level3(f"🖼️  {len(event_obj.images)} images downloaded")
                        formatter.print_event_end()
                        formatter.print_level2("")
                else:
                    formatter.print_info("No events found in this article", level=2)
                formatter.print_article_end()
            
            # Save events to JSON file
            events_output_blog_dir = Path(config.paths.events_output) / self.timestamp / f"{blog.name}.json"
            have_loaded_events_as_json, event_dict_ls = blog.load_events_as_json(events_output_blog_dir)
            
            if have_loaded_events_as_json:
                formatter.print_level1("")
                formatter.print_success(f"Events saved to: {events_output_blog_dir}")
                formatter.print_success(f"Number of events: {len(event_dict_ls)}")
            else:
                formatter.print_level1("")
                formatter.print_warning(f"No events found for {blog.name}")
            formatter.print_box_end(bottom_line)
        
        # Handle review and edit process
        self.handle_events_review(self.events_output_dir)
        
        # Record processing attempts in database with final event counts
        formatter.print_section("Recording processed articles to database...")
        formatter.print_section_end()
        
        # Proceed with merge process
        merged_file_path = self.merge_events()

        # Upload to S3 after successful processing
        self.upload_to_s3(merged_file_path)

        # Clean up temporary folders
        cleanup_temp_folders(self.feed_dir, self.articles_output_dir)

        # Record processing results in database
        for blog in self.blogs:
            for article_obj in blog.articles:
                execute_query(
                    "INSERT INTO processed_articles (blog_name, post_id, timestamp, num_events) VALUES (?, ?, ?, ?)",
                    (article_obj.blog, article_obj.post_id, article_obj.timestamp, len(article_obj.events))
                )
            formatter.print_item(f"{blog.name}: {len(blog.articles)} articles recorded")
        
        formatter.print_header("✨ Run completed successfully!")

    def handle_events_review(self, events_dir: Path) -> None:
        """Handle the review and edit process for events.
        
        Launches a Streamlit web application that allows users to review and
        edit extracted events before merging. The app provides an interactive
        interface for modifying event data.
        
        Args:
            events_dir (Path): Directory containing event files to review
        """
        confirmation = input("│ Do you want to review and edit the events? (Y/N): ").strip().upper()
        
        if confirmation == 'Y':
            print("│")
            print("│ Launching the web event editor...")
            
            try:
                # Get the current working directory
                current_dir = Path.cwd()
                
                print("│ 🚀 Starting Streamlit app...")
                
                # Launch Streamlit using venv_main Python environment
                if sys.platform == "win32":
                    # On Windows, use venv_main Python executable
                    venv_python = Path.cwd() / "venv_main" / "Scripts" / "python.exe"
                    cmd = f'"{venv_python}" -m streamlit run src/ui/main_app.py --server.headless=false -- --events-output "{events_dir}"'
                    process = subprocess.Popen(cmd, shell=True, cwd=current_dir)
                else:
                    # On Unix-like systems, use venv_main Python executable
                    venv_python = Path.cwd() / "venv_main" / "bin" / "python"
                    cmd = [str(venv_python), "-m", "streamlit", "run", "src/ui/main_app.py", "--server.headless=false", "--", "--events-output", str(events_dir)]
                    process = subprocess.Popen(cmd, cwd=current_dir)
                
                print("│")
                input("│ Press Enter when done editing in the browser...")
                
                # Terminate the Streamlit process
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print("│ ✅ Streamlit app stopped")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print("│ ⚠️  Streamlit app force-stopped")
                except Exception as e:
                    print(f"│ ⚠️  Error stopping Streamlit: {str(e)}")
                        
            except Exception as e:
                print(f"│ ❌ Error launching Streamlit app: {str(e)}")
                input("│ Press Enter to continue without editing...")
            
            # Update events after editing
            for blog in self.blogs:
                for article in blog.articles:
                    article.update_events()
            print("│ Articles updated successfully.")
        else:
            print("│ Edit operation cancelled.")

    def merge_events(self) -> Optional[Path]:
        """Merge all blog events into a single file and return the file path.
        
        Combines all event files from different blogs into a single JSON file
        with sequential event IDs. Asks for user confirmation before proceeding.
        
        Returns:
            Optional[Path]: Path to the merged events file, or None if merge was cancelled
        """
        timestamp_dir = Path(config.paths.events_output) / self.timestamp
        blog_events_file_path_ls = list(timestamp_dir.glob("*.json"))
        
        if not blog_events_file_path_ls:
            print("\nNo event files found to merge.")
            return None

        # Show details of each file before asking for merge confirmation
        print("\n📋 Files ready for merging:")
        for blog_event_file_path in blog_events_file_path_ls:
            print(f"\n📄 {blog_event_file_path.name}")
            try:
                with open(blog_event_file_path, 'r', encoding="utf-8") as f:
                    blog_events = json.load(f)

                    print(f"   📊 Contains {len(blog_events)} events")
                    print(f"   🖼️ Contains {sum(len(event.get('images', [])) for event in blog_events)} images")
                            
            except Exception as e:
                print(f"   ❌ Error reading file: {str(e)}")

        merge_confirm = input("\nDo you want to merge the events now? (Y/N): ").strip().upper()
        if merge_confirm.lower() != 'y':
            print("\nMerge operation cancelled.")
            return None

        # Ask user for filename
        filename = input("\nEnter filename for merged events (without .json extension): ").strip()
        if not filename:
            filename = "events"  # Default filename if empty
        
        # Add .json extension if not present
        if not filename.endswith('.json'):
            filename += '.json'

        try:
            total_events: List[Dict[str, Any]] = []
            
            # Get the current event index from database
            current_index = execute_query(
                "SELECT COALESCE(SUM(num_events), 0) as total FROM processed_articles WHERE timestamp != ?", 
                (self.timestamp,)
            ).fetchone()[0]

            print(f"\nStarting from event index: {current_index}")
            
            # Process each blog's events file
            for blog_event_file_path in blog_events_file_path_ls:
                print(f"Reading {blog_event_file_path.name}...")
                try:
                    with open(blog_event_file_path, 'r', encoding="utf-8") as f:
                        blog_events = json.load(f)
                        
                        # Update event indices
                        for event in blog_events:
                            current_index += 1
                            event['id'] = str(current_index)
                        
                        total_events.extend(blog_events)
                except Exception as e:
                    print(f"Error reading {blog_event_file_path.name}: {str(e)}")
                    continue

            print(f"Total new events merged: {len(total_events)}")

            # Save merged events
            merged_events_file_path = Path('data') / filename
            with open(merged_events_file_path, 'w', encoding='utf-8') as f:
                json.dump(total_events, f, indent=2, ensure_ascii=False)
            
            print(f"\nMerged events saved in {merged_events_file_path}")
            return merged_events_file_path
            
        except Exception as e:
            print(f"\n[Error] on Run.merge_events(): {str(e)}")
            raise

    def upload_to_s3(self, merged_file_path: Optional[Path] = None) -> None:
        """Upload processed files to AWS S3 using S3 service.
        
        Uploads the timestamp directory containing all processed files and
        optionally the merged events file to AWS S3 for backup and sharing.
        
        Args:
            merged_file_path (Optional[Path]): Path to the merged events file to upload
        """
        try:
            s3_client = S3()
            
            # Check if there are files to upload
            if not self.timestamp_dir.exists() or not any(self.timestamp_dir.iterdir()):
                formatter.print_warning("No files found to upload to S3")
                return
                
            formatter.print_section("AWS S3 Upload")
            formatter.print_info("Ready to upload files to AWS S3:")
            formatter.print_item(f"📁 Timestamp directory: {self.timestamp_dir}")
            if merged_file_path and merged_file_path.exists():
                formatter.print_item(f"📄 Merged events file: {merged_file_path.name}")
                
            upload_confirm = input("| Do you want to upload to S3? (Y/N): ").strip().upper()
            if upload_confirm != 'Y':
                formatter.print_warning("S3 upload cancelled")
                return
                
            # Upload timestamp directory
            try:
                s3_client.upload_directory(self.timestamp_dir, base_dir=self.events_output_dir)
                formatter.print_success(f"✅ Successfully uploaded directory: {self.timestamp_dir}")
            except Exception as e:
                formatter.print_error(f"Failed to upload directory: {str(e)}")
                raise
                
            # Upload merged events file if provided
            if merged_file_path and merged_file_path.exists():
                try:
                    s3_client.upload_file(merged_file_path, base_dir=merged_file_path.parent)
                    formatter.print_success(f"✅ Successfully uploaded file: {merged_file_path}")
                except Exception as e:
                    formatter.print_error(f"Failed to upload merged file: {str(e)}")
                    raise
                    
            formatter.print_section_end()
        except Exception as e:
            formatter.print_error(f"S3 upload failed: {str(e)}")
            formatter.print_warning("Continuing without S3 upload...")


if __name__ == "__main__":
    # Get timestamp from user input
    timestamp = input("What timestamp do you want? ")
    run = Run(timestamp)
    
    # For testing specific functionality
    # run.start()  # Uncomment to run full workflow
    file_path = run.merge_events()
    run.upload_to_s3(file_path)