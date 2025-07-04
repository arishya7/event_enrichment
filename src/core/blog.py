from dataclasses import dataclass, field, asdict
from typing import List, Dict
from pathlib import Path
import xml.etree.ElementTree as ET
import json

from src.utils.config import config
from src.utils.text_utils import *
from src.core import Article, Event  # Assuming you moved Article to its own file
from src.core.database import execute_query
from src.utils import file_utils

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


    def parse_feed_file(self) -> List[Article]:
        feed_filepath = Path(config.paths.temp_feed) / f"{self.name}.xml"
        articles_ls = []
        articles_file_ls = []
        new_guids = []
        total_articles = 0
        repeated_articles = 0
        article_filepath = '' 

        try:
            tree = ET.parse(feed_filepath)
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
                article_filepath = Path(config.paths.temp_articles_output) / f"{self.name}.json"
                with open(article_filepath, 'w', encoding='utf-8') as f:
                    json.dump(articles_file_ls, f, indent=2, ensure_ascii=False)

            return articles_ls, article_filepath

        except FileNotFoundError:
            print(f"[ERROR][Blog.parse_feed_file] Feed file not found: {feed_filepath}")
            return articles_ls, ""
        except ET.ParseError:
            print(f"[ERROR][Blog.parse_feed_file] Invalid XML format in feed file: {feed_filepath}")
            return articles_ls, ""
        except Exception as e:
            print(f"[ERROR][Blog.parse_feed_file] Failed to parse feed file for {self.name}: {str(e)}")
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
            print(f"[ERROR][Blog.load_events_as_json] No articles found for blog {self.name}")
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