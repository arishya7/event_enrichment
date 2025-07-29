from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import xml.etree.ElementTree as ET
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, UrlContext
import json
from pathlib import Path

from src.utils import *
from src.core.event import Event
from src.services import *

@dataclass
class Article:
    """Class representing an article with all its details.
    
    This class encapsulates article data extracted from RSS/Atom feeds and
    provides methods for extracting events from the article content using AI.
    
    Args:
        title (str): Article title (required)
        blog (str): Name of the blog/source (required)
        timestamp (str): Timestamp when article was scraped (required)
        author (str): Article author (required)
        categories (List[str]): List of article categories/tags (required)
        content (str): Article content/body text (required)
        guid (str): Globally unique identifier for the article (required)
        post_id (int): Numeric post identifier (required)
        
    Attributes:
        Auto-initialized (set in __post_init__):
            events (List[Event]): List of events extracted from this article (default: [])
    """
    # Required input fields
    title: str
    blog: str
    timestamp: str
    author: str
    categories: List[str]
    content: str
    guid: str
    post_id: int
    
    # Auto-initialized fields
    events: List[Event] = field(default_factory=list)

    @staticmethod
    def _find_content(entry: ET.Element) -> str:
        """Find content in an XML entry by trying various tag patterns.
        
        Searches for content in RSS/Atom feed entries using a priority-ordered
        list of known content tags, then falls back to searching for any tag
        containing 'content' or 'description'.
        
        Args:
            entry (ET.Element): XML element to search for content
            
        Returns:
            str: Found content or empty string if no content found
        """
        # Priority ordered list of known content tags
        known_content_tags = [
            '{http://purl.org/rss/1.0/modules/content/}encoded',
            'content:encoded',
            '{http://purl.org/feed/1.0/modules/content/}encoded',
            '{http://www.w3.org/2005/Atom}content',
            'content',
            'description',
            'summary'
        ]
        
        # First try known tags
        for tag in known_content_tags:
            content = entry.findtext(tag, '')
            if content:
                return content
                
        # If no content found, try to find any tag containing 'content' or 'description'
        for elem in entry.iter():
            tag = elem.tag.lower()
            if 'content' in tag or 'description' in tag:
                if elem.text:
                    return elem.text
                    
        return ''

    @classmethod
    def from_entry(cls, entry: ET.Element, is_atom: bool, blog_name: str, timestamp: str) -> Optional["Article"]:
        """Creates an Article instance from an XML feed entry.
        
        Parses RSS or Atom feed entries to extract article metadata and content.
        Handles different XML namespaces and tag structures for each feed type.
        
        Args:
            entry (ET.Element): XML element containing article data
            is_atom (bool): Whether the feed is Atom format (True) or RSS format (False)
            blog_name (str): Name of the blog/source
            timestamp (str): Timestamp of when article was scraped
            
        Returns:
            Optional[Article]: Article instance if parsing successful, None if parsing fails
        """
        try:
            if is_atom:
                # Parse Atom feed entry
                guid = entry.findtext('{http://www.w3.org/2005/Atom}id', '')
                post_id = extract_post_id_atom(guid)
                title = clean_html(entry.findtext('{http://www.w3.org/2005/Atom}title', ''))
                author = clean_html(entry.findtext('.//{http://www.w3.org/2005/Atom}name', ''))
                categories = [clean_html(cat.get('term', '')) for cat in entry.findall('{http://www.w3.org/2005/Atom}category')]
            else:
                # Parse RSS feed entry
                guid = entry.findtext('guid', '')
                post_id = extract_post_id(guid)
                title = clean_html(entry.findtext('title', ''))
                author = clean_html(entry.findtext('{http://purl.org/dc/elements/1.1/}creator', ''))
                categories = [clean_html(cat.text) for cat in entry.findall('category')]

            # Find and clean content for both Atom and RSS
            content = preserve_links_html(cls._find_content(entry))

            return cls(
                title=title,
                blog=blog_name,
                timestamp=timestamp,
                author=author,
                categories=categories,
                content=content,
                guid=guid,
                post_id=post_id
            )
            
        except Exception as e:
            formatter.print_error(f"Failed to parse entry for {blog_name}: {str(e)}")
            return None

    def extract_events(self) -> List[Event]:
        """Extract events from the article using Gemini API.
        
        Uses a two-step process:
        1. Internet-enabled search to gather context about events mentioned in the article
        2. Schema-based formatting to structure the events according to the defined schema
        
        Returns:
            List[Event]: List of extracted events, empty list if none found or error occurs
        """
        try:
            # First API call - Internet search for context
            config_st = GenerateContentConfig(
                system_instruction=config.system_instructions.with_internet,
                tools=[Tool(url_context=UrlContext), Tool(google_search=GoogleSearch)],
                response_modalities=["TEXT"]
            )
            
            int_response = custom_gemini_generate_content(
                prompt=self._format_for_model(),
                config=config_st,
                model=config.gemini_model,
                google_api_key=config.google_api_key
            )
            
            if not int_response:
                return []
                
            # Second API call - Schema formatting
            config_nd = GenerateContentConfig(
                system_instruction=config.system_instructions.with_schema,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=config.event_schema
            )
            
            schema_response = custom_gemini_generate_content(
                prompt=int_response.text,
                config=config_nd,
                model=config.gemini_model,
                google_api_key=config.google_api_key
            )
            
            if not schema_response:
                return []
                
            # Parse and validate events
            is_valid, error_msg, events_dict_ls = is_valid_json(clean_text(schema_response.text))
            if not is_valid:
                formatter.print_error(f"Invalid JSON response: {error_msg}")
                return []
            
            events_obj_ls = []
            for event_dict in events_dict_ls:
                try:
                    event_obj = Event.from_dict(event_dict)
                    events_obj_ls.append(event_obj)
                except Exception as e:
                    formatter.print_error(f"Failed to parse event: {str(e)}")
                    continue
                    
            return events_obj_ls
            
        except Exception as e:
            formatter.print_error(f"Failed to extract events from article {self.guid}: {str(e)}")
            return []
        

    def _format_for_model(self) -> str:
        """Format article content for the AI model input.
        
        Creates a structured prompt containing all relevant article information
        for the Gemini API to process and extract events.
        
        Returns:
            str: Formatted article content for AI model consumption
        """
        return f"""
        Article title: {self.title}
        GUID: {self.guid}
        post_id: {self.post_id}
        article_website: {self.blog}
        Categories: {', '.join(self.categories)}

        Content:
        {self.content}"""

    def update_events(self) -> None:
        """Update article's events from the edited blog-specific JSON file.
        
        This method should be called after manual edits to the blog's JSON file
        to update the article's events before merging. It reads the blog-specific
        events file and matches events to this article using the article's GUID.
        
        Raises:
            Exception: If there's an error reading the file or parsing events
        """
        try:
            # Get path to the blog-specific events file
            blog_events_file_path = Path(config.paths.events_output) / self.timestamp / f"{self.blog}.json"
            
            if not blog_events_file_path.exists():
                formatter.print_error(f"Events file not found for blog {self.blog}")
                return
            
            # Read the edited events
            with open(blog_events_file_path, 'r', encoding='utf-8') as f:
                blog_events: List[Dict[str, Any]] = json.load(f)
            
            # Find events that belong to this article by matching guid
            updated_events = []
            for event_dict in blog_events:
                if event_dict.get('article_guid') == self.guid:
                    try:
                        event_obj = Event.from_dict(event_dict)
                        updated_events.append(event_obj)
                    except Exception as e:
                        formatter.print_error(f"Failed to parse updated event: {str(e)}")
                        continue
            
            # Update the article's events
            self.events = updated_events
            
        except Exception as e:
            formatter.print_error(f"Failed to update events for article {self.guid}: {str(e)}")
            raise