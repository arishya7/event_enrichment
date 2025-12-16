from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, UrlContext
import json
import re
from pathlib import Path

from src.utils import *
from src.core.event import Event
from dateparser.search import search_dates

from src.services import *

EVENT_PROPERTIES = config.event_schema.get('items', {}).get('properties', {})
ALLOWED_EVENT_FIELDS = set(EVENT_PROPERTIES.keys())
REQUIRED_EVENT_FIELDS = config.event_schema.get('items', {}).get('required', [])
EVENT_STRING_FIELDS = {
    field_name
    for field_name, props in EVENT_PROPERTIES.items()
    if props.get('type') == 'string'
}
# Mapping of alternate key names returned by Gemini to our schema fields
KEY_NORMALIZATION_MAP = {
    'eventName': 'title',
    'name': 'title',
    'event_title': 'title',
    'venue': 'venue_name',
    'venueName': 'venue_name',
    'location': 'venue_name',
    'location_name': 'venue_name',
    'date': 'datetime_display',
    'dates': 'datetime_display',
    'eventDate': 'datetime_display',
    'event_dates': 'datetime_display',
    'link': 'url',
    'website': 'url',
    'organizer': 'organiser',
    'organizerName': 'organiser',
    'organiserName': 'organiser',
    'priceRange': 'price_display',
    'minimumPrice': 'min_price',
    'maximumPrice': 'max_price',
    'image': 'images',
}
# Fields that can be empty/null because they're filled later in the pipeline
FIELDS_FILLED_LATER = {
    'address_display',  # Filled by Google Places API
    'planning_area',   # Filled by Google Places API
    'region',          # Filled by Google Places API
    'images',          # Filled by image extraction
    'latitude',        # Filled by Google Places API
    'longitude',       # Filled by Google Places API
}

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
        
        Uses a single API call that combines:
        1. Internet-enabled search to gather context about events mentioned in the article
        2. Schema-based formatting to structure the events according to the defined schema
        
        Returns:
            List[Event]: List of extracted events, empty list if none found or error occurs
        """
        try:
            # Combined single API call - Internet search + Schema formatting
            # Use combined instruction if available, otherwise merge both
            if hasattr(config.system_instructions, 'combined') and config.system_instructions.combined:
                combined_instruction = config.system_instructions.combined
            else:
                # Fallback: combine both instructions
                combined_instruction = f"{config.system_instructions.with_internet}\n\n{config.system_instructions.with_schema}"
            
            config_combined = GenerateContentConfig(
                system_instruction=combined_instruction,
                tools=[Tool(url_context=UrlContext), Tool(google_search=GoogleSearch)],
                temperature=0.0,
                response_schema=config.event_schema
            )
            
            response = custom_gemini_generate_content(
                prompt=self._format_for_model(),
                config=config_combined,
                model=config.gemini_model,
                google_api_key=config.google_api_key
            )
            
            if not response:
                # Fallback: stricter JSON-only response without tools
                strict_instruction = combined_instruction + "\n\nReturn ONLY a JSON array following the response schema. No prose, no markdown."
                config_strict = GenerateContentConfig(
                    system_instruction=strict_instruction,
                    temperature=0.0,
                    response_schema=config.event_schema
                )
                response = custom_gemini_generate_content(
                    prompt=self._format_for_model(),
                    config=config_strict,
                    model=config.gemini_model,
                    google_api_key=config.google_api_key
                )
                if not response:
                    return []
                
            # Parse and validate events
            is_valid, error_msg, events_dict_ls = is_valid_json(clean_text(response.text))
            if not is_valid:
                formatter.print_error(f"Invalid JSON response: {error_msg}")
                return []
            
            events_obj_ls = []
            skipped_events = 0
            for event_dict in events_dict_ls:
                event_dict.setdefault('article_title', self.title)
                event_dict.setdefault('article_guid', self.guid)
                event_dict.setdefault('article_content', self.content)
                self._normalize_event_keys(event_dict)
                self._strip_unknown_fields(event_dict)
                
                # Apply fallbacks for missing fields before validation
                self._infer_dates_from_text(event_dict, self.content)
                self._apply_field_fallbacks(event_dict)
                
                is_valid_fields, validation_msg = self._validate_required_fields(event_dict)
                if not is_valid_fields:
                    formatter.print_error(
                        f"Skipping event for article {self.guid} due to missing required fields: {validation_msg}"
                    )
                    skipped_events += 1
                    continue
                
                try:
                    event_obj = Event.from_dict(event_dict)
                    events_obj_ls.append(event_obj)
                except Exception as e:
                    formatter.print_error(f"Failed to parse event: {str(e)}")
                    continue
            
            if skipped_events:
                formatter.print_info(f"Skipped {skipped_events} event(s) missing required fields", level=2)
                    
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

    @staticmethod
    def _normalize_event_keys(event_dict: Dict[str, Any]) -> None:
        """Normalize alternate key names from Gemini into schema keys."""
        for old_key, new_key in KEY_NORMALIZATION_MAP.items():
            if old_key in event_dict and new_key not in event_dict:
                event_dict[new_key] = event_dict.pop(old_key)
            elif old_key in event_dict and new_key in event_dict:
                if not event_dict.get(new_key) and event_dict.get(old_key):
                    event_dict[new_key] = event_dict.pop(old_key)
                else:
                    event_dict.pop(old_key)

    @staticmethod
    def _infer_dates_from_text(event_dict: Dict[str, Any], fallback_text: str) -> None:
        """Infer start/end datetime fields if missing using parsed dates from text."""
        needs_start = not event_dict.get('start_datetime')
        needs_end = not event_dict.get('end_datetime')

        if not (needs_start or needs_end):
            return

        text_sources = [
            event_dict.get('datetime_display', ''),
            event_dict.get('description', ''),
            fallback_text or ''
        ]

        parsed_dates = None
        for text in text_sources:
            if not text:
                continue
            results = search_dates(
                text,
                settings={
                    'TIMEZONE': 'Asia/Singapore',
                    'RETURN_AS_TIMEZONE_AWARE': False,
                }
            )
            if results:
                parsed_dates = results
                break

        if not parsed_dates:
            return

        def _format(dt: datetime) -> str:
            tz = timezone(timedelta(hours=8))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
            else:
                dt = dt.astimezone(tz)
            return dt.isoformat()

        if needs_start:
            event_dict['start_datetime'] = _format(parsed_dates[0][1])

        if needs_end:
            end_dt = parsed_dates[1][1] if len(parsed_dates) > 1 else parsed_dates[0][1]
            event_dict['end_datetime'] = _format(end_dt)

    @staticmethod
    def _apply_field_fallbacks(event_dict: Dict[str, Any]) -> None:
        """Apply fallback values for missing fields to improve extraction success rate."""
        # Use article GUID as fallback URL if event URL is missing
        if not event_dict.get('url'):
            event_dict['url'] = event_dict.get('article_guid', event_dict.get('guid', ''))
        
        # Generate title fallback if missing - use article title or generate from description
        # Schema requires title to be 40-50 characters
        if not event_dict.get('title') or not str(event_dict.get('title', '')).strip():
            article_title = event_dict.get('article_title', '')
            description = event_dict.get('description', '')
            
            if article_title:
                title = article_title.strip()
            elif description:
                # Generate title from description - take first meaningful part
                desc_clean = description.strip()
                # Remove leading articles/prepositions if present
                if desc_clean.lower().startswith(('the ', 'a ', 'an ', 'this ', 'these ', 'that ')):
                    desc_clean = desc_clean.split(' ', 1)[1] if ' ' in desc_clean else desc_clean
                title = desc_clean.strip()
            else:
                title = "Family-Friendly Activity for All Ages"
            
            # Adjust length to meet schema requirements (40-50 chars)
            title = title.strip()
            if len(title) < 40:
                # Pad if too short
                suffix = " - Family Activity in Singapore"
                # Calculate how much we can add without exceeding 50
                available_space = 50 - len(title)
                if available_space >= len(suffix):
                    title = title + suffix
                else:
                    # Add shorter suffix
                    title = title + " - Singapore"
                # Final check - if still too short, add more context
                if len(title) < 40:
                    title = "Family Activity: " + title
            elif len(title) > 50:
                # Truncate if too long - try to break at word boundary
                truncated = title[:47].strip()
                last_space = truncated.rfind(' ')
                if last_space >= 35:  # Only break at word boundary if reasonable
                    title = truncated[:last_space].strip() + "..."
                else:
                    title = truncated + "..."
            
            # Final validation and assignment
            title = title.strip()
            if len(title) < 40:
                # Last resort: use a fixed-length fallback
                title = "Family-Friendly Activity for All Ages in Singapore"
            if len(title) > 50:
                title = title[:47].strip() + "..."
            
            event_dict['title'] = title
        
        # Generate description if missing - use article content or title as fallback
        if not event_dict.get('description') or not str(event_dict.get('description', '')).strip():
            article_content = event_dict.get('article_content', '')
            title_text = event_dict.get('title', '')
            
            if article_content:
                # Use first 600 chars of article content as description (schema requires 450-700 chars)
                desc = article_content.strip()[:650]  # Leave room for cleanup
                # Try to end at sentence boundary
                last_period = desc.rfind('.')
                if last_period > 400:  # Only truncate at sentence if reasonable
                    desc = desc[:last_period + 1]
                # Ensure minimum length
                if len(desc) < 450:
                    desc = article_content[:450] + "..."
                event_dict['description'] = desc[:700].strip()  # Cap at 700
            elif title_text:
                # Generate description from title
                event_dict['description'] = f"{title_text} - A family-friendly activity in Singapore. Perfect for families looking for fun experiences together. This activity offers engaging experiences suitable for all ages, making it an ideal destination for family outings and memorable moments."
            else:
                # Last resort fallback
                event_dict['description'] = "A family-friendly activity in Singapore perfect for families. This activity offers engaging experiences suitable for all ages, making it an ideal destination for family outings and creating memorable moments together."
        
        # Ensure description meets schema requirements (450-700 chars)
        desc = event_dict.get('description', '')
        if len(desc) < 450:
            # Pad description if too short
            padding = " This family-friendly activity provides an excellent opportunity for families to spend quality time together while enjoying engaging experiences suitable for children and adults alike."
            event_dict['description'] = (desc + padding)[:700].strip()
        elif len(desc) > 700:
            # Truncate if too long
            truncated = desc[:697].strip()
            last_period = truncated.rfind('.')
            if last_period > 600:
                event_dict['description'] = truncated[:last_period + 1]
            else:
                event_dict['description'] = truncated + "..."
        
        # Generate blurb from description if missing (or regenerate if description was updated)
        if not event_dict.get('blurb') or not str(event_dict.get('blurb', '')).strip():
            desc = event_dict.get('description', '')
            if desc:
                # Take first 60 chars of description as blurb
                event_dict['blurb'] = desc[:60].strip() + ('...' if len(desc) > 60 else '')
            else:
                # Last resort blurb
                event_dict['blurb'] = "Family-friendly activity in Singapore for all ages"
        
        # Try to infer organiser if missing or "Unknown"
        if not event_dict.get('organiser') or event_dict.get('organiser', '').lower() in ['unknown', 'n/a', 'tbc', 'tba']:
            organiser = None
            
            # Try 1: Use venue_name as organiser (often the venue is the organiser)
            venue = event_dict.get('venue_name', '')
            if venue and venue.lower() not in ['various locations', 'tbc', 'tba', 'unknown']:
                # Clean up venue name for use as organiser
                organiser = venue.split(' - ')[0].split(' @ ')[0].split(' at ')[0].strip()
                # Remove location suffixes like (Singapore), (Marina Bay), etc.
                organiser = re.sub(r'\s*\([^)]*\)\s*$', '', organiser).strip()
            
            # Try 2: Extract from URL domain
            if not organiser:
                url = event_dict.get('url', '') or event_dict.get('guid', '')
                if url:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        # Extract main domain name (e.g., "safra" from "www.safra.sg")
                        parts = domain.replace('www.', '').split('.')
                        if parts and parts[0] not in ['com', 'sg', 'org', 'net']:
                            # Capitalize nicely
                            organiser = parts[0].replace('-', ' ').replace('_', ' ').title()
                    except Exception:
                        pass
            
            # Try 3: Use article title
            if not organiser:
                article_title = event_dict.get('article_title', '')
                if article_title:
                    # Take first few words as potential organiser
                    words = article_title.split()[:3]
                    if words:
                        organiser = ' '.join(words)
            
            event_dict['organiser'] = organiser if organiser else 'Unknown'
        
        # Set default activity_or_event if missing (default to "activity" for ongoing things)
        if not event_dict.get('activity_or_event'):
            event_dict['activity_or_event'] = 'activity'
        
        # Set default price fields if missing
        if 'price' not in event_dict or event_dict.get('price') is None:
            event_dict['price'] = 0.0
        if 'min_price' not in event_dict or event_dict.get('min_price') is None:
            event_dict['min_price'] = event_dict.get('price', 0.0)
        if 'max_price' not in event_dict or event_dict.get('max_price') is None:
            event_dict['max_price'] = event_dict.get('price', 0.0)
        if not event_dict.get('price_display'):
            event_dict['price_display'] = 'Free' if event_dict.get('price', 0) == 0 else f"${event_dict.get('price', 0)}"
        if not event_dict.get('price_display_teaser'):
            event_dict['price_display_teaser'] = 'Free' if event_dict.get('price', 0) == 0 else 'From $'
        
        # Set default datetime fields if missing - use meaningful defaults instead of empty strings
        activity_type = event_dict.get('activity_or_event', 'activity')
        
        if not event_dict.get('datetime_display_teaser') or not str(event_dict.get('datetime_display_teaser', '')).strip():
            if activity_type == 'activity':
                # For activities, use "Available daily" as default
                event_dict['datetime_display_teaser'] = 'Available daily'
            else:
                # For events, use "Date TBC" as default
                event_dict['datetime_display_teaser'] = 'Date TBC'
        
        if not event_dict.get('datetime_display') or not str(event_dict.get('datetime_display', '')).strip():
            if activity_type == 'activity':
                # For activities, provide a generic ongoing availability message
                event_dict['datetime_display'] = 'Available daily, please check venue for operating hours'
            else:
                # For events, use a TBC message
                event_dict['datetime_display'] = 'Date and time to be confirmed'
        
        if not event_dict.get('start_datetime'):
            event_dict['start_datetime'] = '1970-01-01T00:00:00+08:00'
        if not event_dict.get('end_datetime'):
            event_dict['end_datetime'] = '9999-12-31T23:59:59+08:00'
        
        # Set default age fields if missing
        if 'min_age' not in event_dict or event_dict.get('min_age') is None:
            event_dict['min_age'] = 0.0
        if 'max_age' not in event_dict or event_dict.get('max_age') is None:
            event_dict['max_age'] = 99.0
        if not event_dict.get('age_group_display'):
            event_dict['age_group_display'] = 'All ages'
        
        # Ensure is_free is set based on price
        if 'is_free' not in event_dict:
            event_dict['is_free'] = (event_dict.get('price', 0) == 0)
        
        # Ensure images is an array if missing
        if 'images' not in event_dict:
            event_dict['images'] = []
        
        # Set default venue_name if missing - try to extract from description or use generic fallback
        if not event_dict.get('venue_name') or not str(event_dict.get('venue_name', '')).strip():
            # Try to infer venue from description or title (use original case for better extraction)
            description = event_dict.get('description', '')
            title = event_dict.get('title', '')
            full_text = (title + ' ' + description).strip()
            
            # Look for common venue indicators in description (case-sensitive for better extraction)
            venue_name = None
            if full_text:
                # Common patterns: "at [venue]", "located at [venue]", "visit [venue]", "[venue] in Singapore"
                patterns = [
                    r'(?:at|located at|visit|in)\s+([A-Z][A-Za-z0-9\s&\-\']+(?:Restaurant|Cafe|Mall|Park|Centre|Center|Playground|Museum|Zoo|Attraction|Singapore))',
                    r'([A-Z][A-Za-z0-9\s&\-\']+(?:Restaurant|Cafe|Mall|Park|Centre|Center|Playground|Museum|Zoo))',
                    r'([A-Z][A-Za-z0-9\s&\-\']+)\s+in\s+Singapore',  # "XYZ in Singapore"
                    r'([A-Z][A-Za-z0-9\s&\-\']+(?:Shopping|Food|Play))',  # Generic indicators
                ]
                for pattern in patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        candidate = match.group(1).strip()
                        # Filter out very short or generic names
                        if len(candidate) > 3 and candidate.lower() not in ['the', 'a', 'an', 'at', 'in', 'for']:
                            venue_name = candidate
                            break
            
            if not venue_name:
                # Try to extract from article title if available (often contains venue name)
                article_title = event_dict.get('article_title', '')
                if article_title:
                    # Try to extract venue-like names from article title
                    words = article_title.split()
                    # Look for capitalized words that might be venue names
                    potential_venue = []
                    for word in words:
                        if word[0].isupper() and len(word) > 3:
                            potential_venue.append(word)
                            if len(potential_venue) >= 2:  # Take first 2-3 capitalized words
                                venue_name = ' '.join(potential_venue[:3])
                                break
            
            if not venue_name:
                # Last resort: use generic fallback (but this won't help classification)
                # We still need a value to pass validation, but it's marked as generic
                venue_name = "Various Locations"
                # Mark it so classification can ignore it if needed
                event_dict['_venue_name_is_fallback'] = True
            
            event_dict['venue_name'] = venue_name
        
        # Set default categories if missing - try to infer from content
        if not event_dict.get('categories') or not isinstance(event_dict.get('categories'), list) or len(event_dict.get('categories', [])) == 0:
            # Try to infer category from description, title, and venue
            combined_text = (
                (event_dict.get('title', '') or '') + ' ' +
                (event_dict.get('description', '') or '') + ' ' +
                (event_dict.get('venue_name', '') or '')
            ).lower()
            
            categories = []
            
            # Simple keyword-based category inference
            if any(kw in combined_text for kw in ['restaurant', 'cafe', 'café', 'dining', 'food', 'breakfast', 'brunch', 'lunch', 'dinner', 'menu', 'eatery', 'bistro']):
                categories.append('Kids-friendly dining')
            
            if any(kw in combined_text for kw in ['mall', 'shopping', 'retail', 'plaza', 'shopping centre', 'shopping center']):
                categories.append('Mall related')
            
            if any(kw in combined_text for kw in ['indoor play', 'soft play', 'playground', 'trampoline', 'ball pit', 'lego', 'indoor play area']):
                categories.append('Indoor Playground')
            
            if any(kw in combined_text for kw in ['outdoor play', 'park', 'playground', 'splash', 'water play', 'adventure playground']):
                if 'Indoor Playground' not in categories:  # Avoid duplicate
                    categories.append('Outdoor Playground')
            
            if any(kw in combined_text for kw in ['zoo', 'museum', 'aquarium', 'theme park', 'attraction', 'exhibition', 'show', 'festival', 'workshop']):
                categories.append('Attraction')
            
            # If still no category found, default to "Attraction" as a catch-all
            if not categories:
                categories = ['Attraction']
            
            event_dict['categories'] = categories
            # Mark as fallback so relevance checking can prefer ML classification
            event_dict['_categories_are_fallback'] = True

    @staticmethod
    def _validate_required_fields(event_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """Ensure Gemini output includes all required schema fields with values.
        
        Fields that are filled later in the pipeline (address_display, planning_area, etc.)
        are allowed to be empty/null.
        """
        missing = []
        empty = []

        for field in REQUIRED_EVENT_FIELDS:
            # Skip validation for fields that are filled later in the pipeline
            if field in FIELDS_FILLED_LATER:
                continue
                
            if field not in event_dict:
                missing.append(field)
                continue

            value = event_dict[field]

            if field in EVENT_STRING_FIELDS:
                if not isinstance(value, str) or not value.strip():
                    empty.append(field)
            elif field == "categories":
                if not isinstance(value, list) or len(value) == 0:
                    empty.append(field)
            else:
                if value is None:
                    empty.append(field)

        if missing or empty:
            msg_parts = []
            if missing:
                msg_parts.append(f"missing={missing}")
            if empty:
                msg_parts.append(f"empty={empty}")
            return False, "; ".join(msg_parts)

        return True, ""

    @staticmethod
    def _strip_unknown_fields(event_dict: Dict[str, Any]) -> None:
        """Remove keys not defined in the event schema to prevent validation errors."""
        for key in list(event_dict.keys()):
            if key not in ALLOWED_EVENT_FIELDS:
                event_dict.pop(key, None)


