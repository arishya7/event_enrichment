from dataclasses import dataclass, field, asdict
from typing import List
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import subprocess
import sys

from src.utils.config import config
from src.utils.text_utils import *
from src.core import *
from src.core.database import execute_query
from src.utils import file_utils
from src.utils.output_formatter import formatter

@dataclass
class Blog:
    name: str
    feed_url: str
    timestamp:str
    articles: List[Article] = field(default_factory=list)

    def _get_events_as_dict(self)->list[Event]:
        ls = []
        for article_obj in self.articles:
            ls += article_obj.events
        return ls

    def extract_feed(self) -> bool:
        """Extract feed by launching manual feed manager.
        
        Returns:
            bool: True if feed file exists after the process, False otherwise
        """
        feed_file_path = Path(config.paths.temp_feed) / f"{self.name}.xml"
        
        # Check if feed file already exists
        if feed_file_path.exists():
            formatter.print_success(f"Feed file already exists for {self.name}")
            formatter.print_level1(f"📁 File: {feed_file_path}")
            
            # Ask if user wants to edit it
            response = input("│ Do you want to edit the existing feed? (Y/N): ").strip().upper()
            if response != 'Y':
                formatter.print_info("Using existing feed file")
                return True
        else:
            formatter.print_info(f"No feed file found for {self.name}")
            formatter.print_level1(f"📁 Will create: {feed_file_path}")
        
        formatter.print_level1("")
        formatter.print_level1("🚀 Launching Feed Manager...")
        formatter.print_level1("📝 Please paste your XML feed content and save it")
        
        try:
            # Get the current working directory
            current_dir = Path.cwd()
            
            # Path to the virtual environment
            if sys.platform == "win32":
                python_exe = current_dir / "venv_app" / "Scripts" / "python.exe"
            else:
                python_exe = current_dir / "venv_app" / "bin" / "python"
            
            # Check if virtual environment exists
            if not python_exe.exists():
                formatter.print_error("Virtual environment not found")
                formatter.print_level1("Please create the virtual environment first:")
                formatter.print_level1("python -m venv venv_app")
                formatter.print_level1("pip install -r requirements_app.txt")
                return False
            
            # Launch Streamlit feed manager
            formatter.print_level1(f"🌐 Starting Feed Manager with {python_exe}")
            
            if sys.platform == "win32":
                cmd = f'"{python_exe}" -m streamlit run src/ui/feed_manager.py --server.headless=false'
                process = subprocess.Popen(cmd, shell=True, cwd=current_dir)
            else:
                cmd = [str(python_exe), "-m", "streamlit", "run", "src/ui/feed_manager.py", "--server.headless=false"]
                process = subprocess.Popen(cmd, cwd=current_dir)
            
            formatter.print_level1("")
            formatter.print_level1(f"📋 Instructions:")
            formatter.print_level1(f"   1. Select '{self.name}' from the blog dropdown")
            formatter.print_level1(f"   2. Paste your XML feed content")
            formatter.print_level1(f"   3. Click 'Save Feed'")
            formatter.print_level1(f"   4. Close the browser tab when done")
            formatter.print_level1("")
            
            input("│ Press Enter when you've finished adding the feed content...")
            
            # Terminate the Streamlit process
            try:
                process.terminate()
                process.wait(timeout=5)
                formatter.print_success("Feed Manager stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                formatter.print_warning("Feed Manager force-stopped")
            except Exception as e:
                formatter.print_warning(f"Error stopping Feed Manager: {str(e)}")
            
            # Check if feed file was created/updated
            if feed_file_path.exists():
                formatter.print_success(f"Feed file ready: {feed_file_path}")
                
                # Show basic stats about the feed
                try:
                    with open(feed_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    root = ET.fromstring(content)
                    root_tag = root.tag
                    is_atom = (root_tag == '{http://www.w3.org/2005/Atom}feed' or 
                              root_tag.endswith('}feed') or
                              'atom' in root_tag.lower())
                    
                    if is_atom:
                        entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                        feed_type = "Atom"
                    else:
                        entries = root.findall('.//item')
                        feed_type = "RSS"
                    
                    formatter.print_level1(f"📊 Feed Type: {feed_type} | Articles: {len(entries)}")
                    
                except Exception as e:
                    formatter.print_warning(f"Could not analyze feed: {str(e)}")
                
                return True
            else:
                formatter.print_error("Feed file was not created")
                formatter.print_level1("Please run the extract_feed() again and save the content")
                return False
                
        except Exception as e:
            formatter.print_error(f"Error launching Feed Manager: {str(e)}")
            return False


    def parse_feed_file(self) -> List[Article]:
        feed_file_path = Path(config.paths.temp_feed) / f"{self.name}.xml"
        articles_ls = []
        articles_file_ls = []
        new_guids = []
        total_articles = 0
        repeated_articles = 0
        article_file_path = '' 

        try:
            tree = ET.parse(feed_file_path)
            root = tree.getroot()

            root_tag = root.tag
            is_atom = (root_tag == '{http://www.w3.org/2005/Atom}feed' or 
                       root_tag.endswith('}feed') or
                       'atom' in root_tag.lower())

            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry') if is_atom else root.findall('.//item')

            for entry in entries:
                total_articles += 1

                # Extract post_id before creating Article
                if is_atom:
                    guid = entry.findtext('{http://www.w3.org/2005/Atom}id', '')
                    post_id = extract_post_id_atom(guid)
                else:
                    guid = entry.findtext('guid', '')
                    post_id = extract_post_id(guid)

                has_processed = execute_query(config.query.is_existing, (self.name, post_id)).fetchone()
                if has_processed:
                    repeated_articles += 1
                    continue

                article = Article.from_entry(entry, is_atom, self.name, self.timestamp)
                if article is None:
                    continue

                articles_ls.append(article)
                new_guids.append(article.post_id)
                articles_file_ls += [asdict(article)]

            if articles_file_ls:
                article_file_path = Path(config.paths.temp_articles_output) / f"{self.name}.json"
                with open(article_file_path, 'w', encoding='utf-8') as f:
                    json.dump(articles_file_ls, f, indent=2, ensure_ascii=False)

            return articles_ls, article_file_path

        except FileNotFoundError:
            formatter.print_error(f"Feed file not found: {feed_file_path}")
            return articles_ls, ""
        except ET.ParseError:
            formatter.print_error(f"Invalid XML format in feed file: {feed_file_path}")
            return articles_ls, ""
        except Exception as e:
            formatter.print_error(f"Failed to parse feed file for {self.name}: {str(e)}")
            return articles_ls, ""
    
    def load_events_as_json(self, path: Path) -> bool:
        """Save blog events to a JSON file.
        
        Args:
            path (Path): Path where to save the JSON file
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        # Validate that blog has articles
        if not self.articles:
            formatter.print_error(f"No articles found for blog {self.name}")
            return False
            
        # Validate that articles have events
        articles_with_events = [article for article in self.articles if article.events]
        if not articles_with_events:
            return False
            
        # Convert events to list of dictionaries
        events_dict_ls = [asdict(event) for event in self._get_events_as_dict()]
        
        # Save to JSON using utility function
        return file_utils.save_to_json(events_dict_ls, path)

if __name__ == "__main__":
    blog = Blog("sassymamasg","")