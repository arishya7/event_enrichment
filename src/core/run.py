from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
import re
from fuzzywuzzy import fuzz
# Lazy load heavy ML libraries
# from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
from src.utils import *
from src.core.blog import Blog
from src.core.event import Event
from src.core.database import *
from src.services import *
from src.core.database import get_db_connection
import os
from src.utils.file_utils import get_next_event_id
from src.utils.output_filter import classify_content
from src.utils.harvest_emails import harvest as harvest_emails_to_excel
from dataclasses import asdict

EMBEDDING_MODEL = "all-mpnet-base-v2"

# Lazy-loaded model cache
_sentence_model = None

def get_sentence_model():
    """Lazy load SentenceTransformer model."""
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        print("   Loading embedding model (first time only)...")
        _sentence_model = SentenceTransformer(EMBEDDING_MODEL)
    return _sentence_model

def get_cosine_sim():
    """Get cosine similarity function from sentence_transformers."""
    from sentence_transformers import util
    return util.cos_sim

@dataclass
class Run:
    """Main orchestrator class for the web scraping and event extraction process.
    
    This class manages the entire workflow from feed extraction to event processing,
    including database operations, file management, and S3 uploads.
    
    Args:
        timestamp (str): Unique timestamp identifier for this run (required)
        blog_name (Optional[str]): Optional blog name to process only one blog. 
                                   If None, processes all blogs. (default: None)
        
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
    blog_name: Optional[str] = None  # Optional: process only this blog
    max_articles: Optional[int] = None  # Optional: limit number of articles per blog
    
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
            # Filter to specific blog if blog_name is specified
            if self.blog_name is None or blog_name == self.blog_name:
                self.blogs.append(Blog(blog_name, blog_feed_url, self.timestamp))
        
        # Validate that blog_name was found if specified
        if self.blog_name and not self.blogs:
            available_blogs = list(config.blog_website.__dict__.keys())
            raise ValueError(f"Blog '{self.blog_name}' not found. Available blogs: {', '.join(available_blogs)}")

    def deduplicate_events_semantic(self, events: List[Event], sim_threshold: float = 0.85) -> List[Event]:
        if not events:
            formatter.print_level2("No events supplied for semantic deduplication — skipping")
            return events

        conn = get_db_connection()
        embeddings_query = """
            SELECT e.id, e.title, e.venue_name, e.start_datetime, e.end_datetime, emb.embedding
            FROM events e
            INNER JOIN event_embeddings emb ON emb.id = e.id
            WHERE emb.embedding_model = %s
        """
        df = pd.read_sql_query(embeddings_query, conn, params=[EMBEDDING_MODEL])
        conn.close()

        formatter.print_level2(f"Loaded {len(df)} stored event embeddings from database")
        formatter.print_level2(f"Checking {len(events)} new events for semantic duplicates (≥ {sim_threshold:.0%} or ≥75% with venue match)")
        
        # Helper to check if event is evergreen (placeholder dates)
        def is_evergreen(start_dt, end_dt) -> bool:
            """Check if event uses placeholder dates (1970-01-01 to 2099-12-31) indicating evergreen."""
            if start_dt is None or end_dt is None:
                return True  # Treat missing dates as evergreen
            try:
                # Handle both string and datetime objects
                if isinstance(start_dt, str):
                    start_str = start_dt[:10] if len(start_dt) >= 10 else start_dt
                else:
                    start_str = start_dt.strftime('%Y-%m-%d') if hasattr(start_dt, 'strftime') else str(start_dt)[:10]
                if isinstance(end_dt, str):
                    end_str = end_dt[:10] if len(end_dt) >= 10 else end_dt
                else:
                    end_str = end_dt.strftime('%Y-%m-%d') if hasattr(end_dt, 'strftime') else str(end_dt)[:10]
                
                # Evergreen markers
                if start_str == '1970-01-01' or end_str == '2099-12-31':
                    return True
                return False
            except Exception:
                return True  # Default to evergreen on error
        
        def dates_overlap(start1, end1, start2, end2) -> bool:
            """Check if two date ranges overlap."""
            try:
                from datetime import datetime
                # Parse dates
                def parse_date(dt):
                    if dt is None:
                        return None
                    if isinstance(dt, str):
                        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    return dt
                
                s1, e1 = parse_date(start1), parse_date(end1)
                s2, e2 = parse_date(start2), parse_date(end2)
                
                if None in (s1, e1, s2, e2):
                    return True  # Assume overlap if dates missing
                
                # Check overlap: ranges overlap if start1 <= end2 and start2 <= end1
                return s1 <= e2 and s2 <= e1
            except Exception:
                return True  # Assume overlap on error

        if df.empty:
            formatter.print_info("Database empty — skipping semantic deduplication.")
            return events

        def normalize_venue_name(venue: str) -> str:
            """Normalize venue name for comparison (lowercase, remove punctuation, extra spaces)"""
            if not venue:
                return ""
            normalized = venue.lower().strip()
            # Remove common suffixes and locations in parentheses
            normalized = re.sub(r'\s*\([^)]*\)', '', normalized)  # Remove (Location)
            normalized = re.sub(r'\s*-\s*[^-]*$', '', normalized)  # Remove trailing " - Location"
            normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace punctuation with space
            normalized = ' '.join(normalized.split())  # Normalize whitespace
            return normalized

        existing_vectors, existing_titles, existing_venue_names, existing_venue_actuals, existing_ids = [], [], [], [], []
        existing_start_dates, existing_end_dates, existing_is_evergreen = [], [], []
        for row in df.itertuples():
            emb_blob = row.embedding
            if emb_blob is None:
                continue
            if isinstance(emb_blob, memoryview):
                emb_blob = emb_blob.tobytes()
            vector = np.frombuffer(emb_blob, dtype=np.float32)
            if vector.size == 0:
                continue
            existing_vectors.append(vector)
            existing_titles.append(row.title or "")
            venue_actual = row.venue_name if hasattr(row, 'venue_name') else ''
            existing_venue_actuals.append(venue_actual)
            existing_venue_names.append(normalize_venue_name(venue_actual))
            existing_ids.append(row.id)
            # Store datetime info
            start_dt = row.start_datetime if hasattr(row, 'start_datetime') else None
            end_dt = row.end_datetime if hasattr(row, 'end_datetime') else None
            existing_start_dates.append(start_dt)
            existing_end_dates.append(end_dt)
            existing_is_evergreen.append(is_evergreen(start_dt, end_dt))

        if not existing_vectors:
            formatter.print_info("No stored embeddings available — skipping semantic deduplication.")
            return events

        existing_embeddings = torch.from_numpy(np.vstack(existing_vectors))
        model = get_sentence_model()
        formatter.print_level3("Encoding new events (batch processing)...")
        # Match the exact format used when storing embeddings: "title blurb description" (space-separated, same order)
        new_texts = [
            " ".join(filter(None, (e.title or '', e.blurb or '', e.description or ''))).strip() or " "
            for e in events
        ]
        new_embeddings = model.encode(new_texts, convert_to_tensor=True, show_progress_bar=False, batch_size=32)

        unique_events, dupes = [], []
        duplicate_count = 0
        cos_sim = get_cosine_sim()

        for event, new_emb in zip(events, new_embeddings):
            sims = cos_sim(new_emb, existing_embeddings)[0]
            max_sim, max_idx = float(torch.max(sims)), int(torch.argmax(sims))
            best_match_title = existing_titles[max_idx]
            best_match_venue = existing_venue_names[max_idx]
            best_match_venue_actual = existing_venue_actuals[max_idx] if max_idx < len(existing_venue_actuals) else ""
            best_match_id = existing_ids[max_idx]
            
            # Get datetime info for best match
            best_match_start = existing_start_dates[max_idx] if max_idx < len(existing_start_dates) else None
            best_match_end = existing_end_dates[max_idx] if max_idx < len(existing_end_dates) else None
            best_match_evergreen = existing_is_evergreen[max_idx] if max_idx < len(existing_is_evergreen) else True
            
            # Check if new event is evergreen
            new_event_evergreen = is_evergreen(event.start_datetime, event.end_datetime)
            
            # Check venue name match (exact match or fuzzy match for similar venues)
            new_venue_normalized = normalize_venue_name(event.venue_name)
            venue_exact_match = new_venue_normalized and best_match_venue and new_venue_normalized == best_match_venue
            # Also check fuzzy match for venues that are very similar (e.g., "fusion spoon" vs "fusion spoon botanic garden")
            venue_fuzzy_match = False
            if new_venue_normalized and best_match_venue and not venue_exact_match:
                # Check if one venue name contains the other (for multi-word venue names)
                if (new_venue_normalized in best_match_venue or best_match_venue in new_venue_normalized) and len(new_venue_normalized) >= 5 and len(best_match_venue) >= 5:
                    venue_fuzzy_match = True
                # Or use fuzzy ratio for very similar names
                elif new_venue_normalized and best_match_venue:
                    venue_ratio = fuzz.ratio(new_venue_normalized, best_match_venue)
                    if venue_ratio >= 85:  # Very similar venue names
                        venue_fuzzy_match = True
            venue_matches = venue_exact_match or venue_fuzzy_match

            # Determine if duplicate based on similarity, venue match, and datetime
            # Be careful: same venue can have different events (e.g., "Gardens by the Bay - Flower Festival" vs "Gardens by the Bay - Christmas Light Show")
            is_duplicate = False
            match_reason = ""
            
            # For time-limited events at same venue, check date overlap
            # If both are time-limited and dates don't overlap, they're different events
            both_time_limited = not new_event_evergreen and not best_match_evergreen
            time_overlap = True  # Default to True (assume overlap)
            if both_time_limited and venue_matches:
                time_overlap = dates_overlap(
                    event.start_datetime, event.end_datetime,
                    best_match_start, best_match_end
                )
            
            if max_sim >= sim_threshold:
                # High semantic similarity (85%+) - definitely a duplicate
                # But for time-limited events at same venue with no date overlap, they might be different
                if both_time_limited and venue_matches and not time_overlap and max_sim < 0.90:
                    # Different time periods at same venue - likely different event
                    pass  # Don't mark as duplicate
                else:
                    is_duplicate = True
                    match_reason = "semantic"
            elif venue_matches and max_sim >= 0.80:
                # Same venue with high similarity (80-85%) - treat as duplicate
                # But check time overlap for time-limited events
                if both_time_limited and not time_overlap:
                    pass  # Different time periods - not a duplicate
                else:
                    is_duplicate = True
                    match_reason = "venue + semantic (high)"
            elif venue_matches and max_sim >= 0.75:
                # Same venue with moderate-high similarity (75-80%) - check title similarity too
                # If titles are also similar, it's likely the same event
                title_similarity = fuzz.ratio(event.title.lower(), best_match_title.lower()) / 100.0
                
                # For time-limited events, also require time overlap
                if both_time_limited and not time_overlap:
                    pass  # Different time periods - not a duplicate
                elif title_similarity >= 0.50:  # Titles are at least 50% similar
                    is_duplicate = True
                    match_reason = "venue + title + semantic"
                # If venue matches exactly and similarity is 75%+, it's likely the same event even with different titles
                elif venue_exact_match and max_sim >= 0.78:
                    if both_time_limited and not time_overlap:
                        pass  # Different time periods
                    else:
                        is_duplicate = True
                        match_reason = "venue (exact) + semantic"
            elif venue_matches and max_sim >= 0.70 and both_time_limited and time_overlap:
                # Lower threshold (70%) for time-limited events at same venue with overlapping dates
                # This helps catch events like "Christmas at Gardens" with slightly different descriptions
                title_similarity = fuzz.ratio(event.title.lower(), best_match_title.lower()) / 100.0
                if title_similarity >= 0.60:
                    is_duplicate = True
                    match_reason = "venue + title + time overlap"

            if is_duplicate:
                duplicate_count += 1
                dupes.append({
                    "event_id": best_match_id,
                    "event_title": best_match_title,
                    "new_event_title": event.title,
                    "new_event_url": event.url,
                    "similarity_score": max_sim,
                    "venue_match": venue_matches,
                })
                formatter.print_level3(f"[DUP] {event.title} ↔ {best_match_title} ({max_sim:.2%}, {match_reason})")
            else:
                unique_events.append(event)

        if dupes:
            dupes_dir = Path("data/duplicates")
            dupes_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(dupes).to_csv(dupes_dir / "semantic_dupes.csv", index=False)

        formatter.print_level2(f"Deduplication complete — {duplicate_count} duplicates removed, {len(unique_events)} unique remain")
        
        # Also deduplicate within the same batch (same article might extract similar events)
        if len(unique_events) > 1:
            formatter.print_level3("Checking for duplicates within same batch...")
            batch_deduped = self._deduplicate_within_batch(unique_events, sim_threshold=sim_threshold)
            if len(batch_deduped) < len(unique_events):
                batch_removed = len(unique_events) - len(batch_deduped)
                formatter.print_level2(f"Removed {batch_removed} duplicate(s) within same batch")
                return batch_deduped
        
        return unique_events
    
    def _deduplicate_within_batch(self, events: List[Event], sim_threshold: float = 0.85) -> List[Event]:
        """Deduplicate events within the same batch/article using semantic similarity with venue matching."""
        if len(events) <= 1:
            return events
        
        def normalize_venue_name(venue: str) -> str:
            """Normalize venue name for comparison (lowercase, remove punctuation, extra spaces)"""
            if not venue:
                return ""
            normalized = venue.lower().strip()
            # Remove common suffixes and locations in parentheses
            normalized = re.sub(r'\s*\([^)]*\)', '', normalized)  # Remove (Location)
            normalized = re.sub(r'\s*-\s*[^-]*$', '', normalized)  # Remove trailing " - Location"
            normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace punctuation with space
            normalized = ' '.join(normalized.split())  # Normalize whitespace
            return normalized
        
        # Combine text for each event - match the format used for database embeddings
        texts = [
            " ".join(filter(None, (e.title or '', e.blurb or '', e.description or ''))).strip() or " "
            for e in events
        ]
        
        # Use cached model
        model = get_sentence_model()
        embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False, batch_size=32)
        
        # Find duplicates using similarity matrix
        cos_sim = get_cosine_sim()
        similarity_matrix = cos_sim(embeddings, embeddings)
        to_remove = set()
        
        for i in range(len(events)):
            if i in to_remove:
                continue
            venue_i = normalize_venue_name(events[i].venue_name)
            for j in range(i + 1, len(events)):
                if j in to_remove:
                    continue
                similarity = float(similarity_matrix[i][j])
                venue_j = normalize_venue_name(events[j].venue_name)
                venue_matches = venue_i and venue_j and venue_i == venue_j
                
                # Determine if duplicate: be careful with same venue having different events
                is_duplicate = False
                match_reason = ""
                if similarity >= sim_threshold:
                    is_duplicate = True
                    match_reason = "semantic"
                elif venue_matches and similarity >= 0.80:
                    # Same venue with high similarity (80%+) - treat as duplicate
                    is_duplicate = True
                    match_reason = "venue + semantic (high)"
                elif venue_matches and similarity >= 0.75:
                    # Same venue with moderate similarity (75-80%) - check title similarity
                    title_similarity = fuzz.ratio(events[i].title.lower(), events[j].title.lower()) / 100.0
                    if title_similarity >= 0.60:  # Titles are at least 60% similar
                        is_duplicate = True
                        match_reason = "venue + title + semantic"
                
                if is_duplicate:
                    # Keep the first one, remove the duplicate
                    to_remove.add(j)
                    formatter.print_level3(f"[BATCH DUP] {events[i].title} ↔ {events[j].title} ({similarity:.2%}, {match_reason})")
        
        # Return only unique events
        return [e for idx, e in enumerate(events) if idx not in to_remove]


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

    def process_raw_events(self, raw_events: List[Dict[str, Any]], source_name: str = "custom") -> List[Event]:
        """Process raw event dictionaries through the full pipeline.
        
        This method takes raw event data (e.g., from CategoryScraper) and processes
        them through the same pipeline as RSS events:
        1. Convert to Event objects
        2. Semantic deduplication
        3. Category filtering
        4. Get address & coordinates
        5. Download images
        6. Save to files
        
        Args:
            raw_events: List of event dictionaries from scraper
            source_name: Name to use for output files (default: "custom")
            
        Returns:
            List of processed Event objects
        """
        from datetime import datetime
        
        init_db()
        
        formatter.print_header(f"Processing {len(raw_events)} raw events")
        
        # Prepare output folders
        relevant_dir = self.timestamp_dir / "relevant"
        nonrelevant_dir = self.timestamp_dir / "non-relevant"
        relevant_dir.mkdir(parents=True, exist_ok=True)
        nonrelevant_dir.mkdir(parents=True, exist_ok=True)
        
        ALLOWED_CATEGORIES = {"Indoor Playground", "Outdoor Playground", "Attraction", "Mall related", "Kids-friendly dining"}
        
        # Convert raw dicts to Event objects
        events: List[Event] = []
        scraped_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for raw in raw_events:
            try:
                # Ensure required fields have defaults
                event = Event(
                    title=raw.get('title', 'Untitled')[:50] if raw.get('title') else 'Untitled',
                    blurb=raw.get('blurb', '')[:60] if raw.get('blurb') else '',
                    description=raw.get('description', '')[:700] if raw.get('description') else '',
                    guid=raw.get('guid', ''),
                    activity_or_event=raw.get('activity_or_event', 'activity'),
                    url=raw.get('url', ''),
                    price_display_teaser=raw.get('price_display_teaser', 'Free'),
                    price_display=raw.get('price_display', 'Free'),
                    price=float(raw.get('price', 0) or 0),
                    organiser=raw.get('organiser', ''),
                    age_group_display=raw.get('age_group_display', 'All ages'),
                    min_age=float(raw.get('min_age', 0) or 0),
                    max_age=float(raw.get('max_age', 99) or 99),
                    datetime_display_teaser=raw.get('datetime_display_teaser', ''),
                    datetime_display=raw.get('datetime_display', ''),
                    start_datetime=raw.get('start_datetime', '1970-01-01T00:00:00+08:00'),
                    end_datetime=raw.get('end_datetime', '2099-12-31T23:59:59+08:00'),
                    venue_name=raw.get('venue_name', ''),
                    categories=raw.get('categories', []) or [],
                    scraped_on=scraped_on,
                    min_price=float(raw.get('min_price', 0) or 0),
                    max_price=float(raw.get('max_price', 0) or 0),
                    keyword_tag=raw.get('keyword_tag', '') if isinstance(raw.get('keyword_tag'), str) else ','.join(raw.get('keyword_tag', [])),
                    skip_url_validation=True,  # Disable URL search API calls for category/single article scraping
                )
                # Copy images if present
                if raw.get('images'):
                    event.images = raw['images']
                events.append(event)
            except Exception as e:
                formatter.print_error(f"Error converting event: {e}")
                continue
        
        formatter.print_success(f"Converted {len(events)} events to Event objects")
        
        # Semantic deduplication
        events = self.deduplicate_events_semantic(events)
        formatter.print_success(f"After deduplication: {len(events)} events")
        
        # Category filtering
        relevant: List[Event] = []
        irrelevant: List[Event] = []
        
        for ev in events:
            ev_dict = asdict(ev)
            cats = set(getattr(ev, "categories", []) or [])
            categories_are_fallback = ev_dict.get('_categories_are_fallback', False)
            
            has_allowed_category = False
            if not categories_are_fallback:
                has_allowed_category = bool(cats & ALLOWED_CATEGORIES)
            
            has_semantic_match = False
            semantic_category = None
            ml_confidence = 0.0
            
            try:
                classification_result = classify_content(ev_dict)
                if classification_result:
                    ml_confidence = classification_result.get('confidence', 0.0)
                    if classification_result.get('is_relevant', False):
                        topic_to_category = {
                            "indoor playground": "Indoor Playground",
                            "outdoor playground": "Outdoor Playground",
                            "kids attractions": "Attraction",
                            "malls": "Mall related",
                            "kids dining": "Kids-friendly dining"
                        }
                        classifier_category = classification_result.get('category', '').lower()
                        semantic_category = topic_to_category.get(classifier_category)
                        has_semantic_match = semantic_category in ALLOWED_CATEGORIES if semantic_category else False
                        
                        if has_semantic_match and semantic_category:
                            ev.categories = [semantic_category]
            except Exception:
                if not has_allowed_category:
                    has_allowed_category = bool(cats & ALLOWED_CATEGORIES)
            
            if has_allowed_category and ml_confidence < 0.50:
                has_allowed_category = False
            
            if has_allowed_category or has_semantic_match:
                relevant.append(ev)
            else:
                irrelevant.append(ev)
        
        formatter.print_success(f"Relevant: {len(relevant)}, Non-relevant: {len(irrelevant)}")
        
        # Assign IDs and process each relevant event
        for event_obj in relevant:
            if not getattr(event_obj, "id", None):
                event_obj.id = get_next_event_id()
            
            formatter.print_level2(f"Processing: {event_obj.title[:40]}...")
            
            # Get address and coordinates
            add_coord_result = event_obj.get_address_n_coord()
            if add_coord_result:
                event_obj.address_display, event_obj.latitude, event_obj.longitude = add_coord_result
                formatter.print_success(f"  Address: {event_obj.address_display[:50]}...", level=3)
                try:
                    if which_district:
                        pa, reg = which_district(event_obj.longitude, event_obj.latitude)
                        if pa:
                            event_obj.planning_area = pa
                        if reg:
                            event_obj.region = reg
                except Exception:
                    pass
            
            # Download images
            event_obj.images = event_obj.get_images(self.image_dir / source_name)
            formatter.print_level3(f"  🖼️ {len(event_obj.images)} images")
        
        # Save to files
        relevant_path = relevant_dir / f"{source_name}.json"
        nonrelevant_path = nonrelevant_dir / f"{source_name}.json"
        
        with open(relevant_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in relevant], f, indent=2, ensure_ascii=False)
        
        with open(nonrelevant_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in irrelevant], f, indent=2, ensure_ascii=False)
        
        formatter.print_success(f"Saved relevant events to: {relevant_path}")
        formatter.print_success(f"Saved non-relevant events to: {nonrelevant_path}")
        
        # Ask about email harvesting
        harvest_choice = input("\n│ Harvest organizer emails from event URLs? (y/n): ").strip().lower()
        if harvest_choice == 'y':
            try:
                formatter.print_section("Harvesting organizer emails...")
                harvest_emails_to_excel(str(self.timestamp_dir), use_playwright=True)
                formatter.print_success(f"Emails saved to: data/emails.xlsx")
                formatter.print_section_end()
            except Exception as e:
                formatter.print_error(f"Email harvesting failed: {e}")
                formatter.print_section_end()
        
        # Ask about review
        self.handle_events_review(self.events_output_dir)
        
        # Merge and upload
        merged_file_path = self.merge_events()
        if merged_file_path:
            self.upload_to_s3(merged_file_path)
        
        return relevant

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
            
            # Prepare output folders and accumulators for this blog
            relevant_dir = self.timestamp_dir / "relevant"
            nonrelevant_dir = self.timestamp_dir / "non-relevant"
            relevant_dir.mkdir(parents=True, exist_ok=True)
            nonrelevant_dir.mkdir(parents=True, exist_ok=True)

            blog_relevant: List[Event] = []
            blog_irrelevant: List[Event] = []
            ALLOWED_CATEGORIES = {"Indoor Playground", "Outdoor Playground", "Attraction", "Mall related", "Kids-friendly dining"}

            # Parse feed and extract articles
            (blog.articles, articles_json_file_path) = blog.parse_feed_file()

            if self.max_articles and len(blog.articles) > self.max_articles:
                formatter.print_info(
                    f"Limiting {blog.name} to first {self.max_articles} articles (requested via CLI option)"
                )
                blog.articles = blog.articles[:self.max_articles]
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

                num_extracted = len(article_obj.events)
                print(f"Number of events before deduplication: {num_extracted}")

                if num_extracted == 0:
                    formatter.print_info("No events found in this article", level=2)
                    formatter.print_article_end()
                    continue

                # Deduplicate events semantically
                article_obj.events = self.deduplicate_events_semantic(article_obj.events)

                # Classify events into relevant and nonrelevant using semantic/topic-based matching
                relevant, irrelevant = [], []
                for ev in article_obj.events:
                    # Convert event to dict for classification
                    ev_dict = asdict(ev)
                    
                    # Semantic classification based on event content (title, description, venue)
                    cats = set(getattr(ev, "categories", []) or [])
                    categories_are_fallback = ev_dict.get('_categories_are_fallback', False)
                    
                    # Only trust Gemini categories if they're not fallback (fallback categories are less reliable)
                    has_allowed_category = False
                    if not categories_are_fallback:
                        has_allowed_category = bool(cats & ALLOWED_CATEGORIES)
                    
                    has_semantic_match = False
                    semantic_category = None
                    
                    ml_confidence = 0.0
                    try:
                        classification_result = classify_content(ev_dict)
                        if classification_result:
                            ml_confidence = classification_result.get('confidence', 0.0)
                            if classification_result.get('is_relevant', False):
                                # Map classifier output to our allowed categories
                                topic_to_category = {
                                    "indoor playground": "Indoor Playground",
                                    "outdoor playground": "Outdoor Playground", 
                                    "kids attractions": "Attraction",  # Fixed: classifier returns "kids attractions" not "attractions"
                                    "malls": "Mall related",
                                    "kids dining": "Kids-friendly dining"
                                }
                                # Extract category from dictionary and convert to lowercase
                                classifier_category = classification_result.get('category', '').lower()
                                semantic_category = topic_to_category.get(classifier_category)
                                has_semantic_match = semantic_category in ALLOWED_CATEGORIES if semantic_category else False
                                
                                # If ML classifier found a match, update the event's category field with the ML result
                                if has_semantic_match and semantic_category:
                                    ev.categories = [semantic_category]
                    except Exception:
                        # If classification fails, fall back to checking Gemini categories (even if fallback)
                        if not has_allowed_category:
                            has_allowed_category = bool(cats & ALLOWED_CATEGORIES)
                    
                    # Stricter logic: ML classifier must agree (confidence >= threshold) even if Gemini assigned category
                    # Only trust Gemini categories if ML classifier also has reasonable confidence (>= 50%)
                    if has_allowed_category and ml_confidence < 0.50:
                        # Gemini assigned category but ML classifier has low confidence - don't trust Gemini alone
                        has_allowed_category = False
                    
                    # Event is relevant if either Gemini categories (with ML support) OR semantic classification matches
                    if has_allowed_category or has_semantic_match:
                        relevant.append(ev)
                    else:
                        irrelevant.append(ev)
                
                article_obj.events = relevant
                blog_relevant.extend(relevant)
                blog_irrelevant.extend(irrelevant)

                # Assign ids to events
                for event_obj in article_obj.events:
                    if not getattr(event_obj, "id", None):
                        event_obj.id = get_next_event_id()
                
                print(f"Number of events after deduplication: {len(article_obj.events)}")

                if article_obj.events:
                    formatter.print_level2(f"✨ Found! Number of events: {len(article_obj.events)}")
                    for event_idx, event_obj in enumerate(article_obj.events, 1):
                        formatter.print_event_start(event_idx, len(article_obj.events))
                        formatter.print_level3(f"➤ {event_obj.title}")
                        
                        # Get address and coordinates for event venue
                        add_coord_result = event_obj.get_address_n_coord()
                        if add_coord_result:
                            event_obj.address_display, event_obj.latitude, event_obj.longitude = add_coord_result
                            formatter.print_success(f"Address & coordinates extracted: {event_obj.address_display}", level=3)
                            # Derive planning area and region if available
                            try:
                                if 'which_district' in globals() or 'which_district' in dir():
                                    pass
                                if which_district:
                                    pa, reg = which_district(event_obj.longitude, event_obj.latitude)
                                    if pa:
                                        event_obj.planning_area = pa
                                    if reg:
                                        event_obj.region = reg
                            except Exception as _:
                                pass
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
            
            # Save relevant and non-relevant events to separate JSON files
            relevant_path = relevant_dir / f"{blog.name}.json"
            nonrelevant_path = nonrelevant_dir / f"{blog.name}.json"

            with open(relevant_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in blog_relevant], f, indent=2, ensure_ascii=False)

            with open(nonrelevant_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in blog_irrelevant], f, indent=2, ensure_ascii=False)

            formatter.print_level1("")
            formatter.print_success(f"Relevant events saved to: {relevant_path}")
            formatter.print_success(f"Relevant count: {len(blog_relevant)}")
            formatter.print_success(f"Non-relevant events saved to: {nonrelevant_path}")
            formatter.print_success(f"Non-relevant count: {len(blog_irrelevant)}")
            formatter.print_box_end(bottom_line)
        
        # Harvest emails from event URLs
        try:
            formatter.print_section("Harvesting organizer emails...")
            harvest_emails_to_excel(str(self.timestamp_dir), use_playwright=True)
            formatter.print_success(f"Emails saved to: data/emails.xlsx")
            formatter.print_section_end()
        except Exception as e:
            formatter.print_error(f"Email harvesting failed: {e}")
            formatter.print_section_end()
        
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
                
                # Launch Streamlit using venv Python environment
                if sys.platform == "win32":
                    # On Windows, use venv Python executable
                    venv_python = Path.cwd() / "venv" / "Scripts" / "python.exe"
                    cmd = f'"{venv_python}" -m streamlit run src/ui/main_app.py --server.headless=false -- --events-output "{events_dir}"'
                    process = subprocess.Popen(cmd, shell=True, cwd=current_dir)
                else:
                    # On Unix-like systems, use venv Python executable
                    venv_python = Path.cwd() / "venv" / "bin" / "python"
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
            formatter.print_item(f"📁 Folder directory: {self.timestamp_dir}")
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