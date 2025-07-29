"""
Event management functions for the Event JSON & Image Editor application.
"""

import json
import re
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from src.ui.constants import EVENTS_OUTPUT_DIR, MAX_IMAGES_PER_EVENT
from src.ui.helpers import (
    extract_image_index, get_existing_indexes, sort_images_by_index,
    generate_image_filename, get_next_available_image_index,
    create_image_object, save_events_to_file
)

# Import Google Places functionality
try:
    from src.services.places import get_coordinates_from_address
    GOOGLE_PLACES_AVAILABLE = True
except (ImportError, ValueError, FileNotFoundError) as e:
    GOOGLE_PLACES_AVAILABLE = False
    
    # Create a dummy function to prevent errors
    def get_coordinates_from_address(address):
        return None, None


class EventManager:
    """Handles event CRUD operations and image management."""
    
    def __init__(self, events: List[Dict], file_path: Path):
        self.events = events
        self.file_path = file_path
    
    def save_events(self) -> None:
        """Save events to file."""
        save_events_to_file(self.events, self.file_path)
    
    def update_event(self, event_idx: int, updated_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an event with new data."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            # Get original event
            original_event = self.events[event_idx]
            event_without_images = {k: v for k, v in original_event.items() if k != "images"}
            
            # Handle coordinate updates if address changed
            coordinates_updated = False
            new_full_address = updated_data.get('full_address', '')
            original_full_address = original_event.get('full_address', '')
            
            latitude = event_without_images.get('latitude', 0.0)
            longitude = event_without_images.get('longitude', 0.0)
            
            if latitude is None:
                latitude = 0.0
            if longitude is None:
                longitude = 0.0
            
            
            if (new_full_address != original_full_address and 
                new_full_address and new_full_address.strip() and 
                GOOGLE_PLACES_AVAILABLE):
                new_longitude, new_latitude = get_coordinates_from_address(new_full_address)    
                if new_longitude is not None and new_latitude is not None:
                    longitude = new_longitude
                    latitude = new_latitude
                    coordinates_updated = True

            
            # Build updated event data
            updated_event_data = self._build_updated_event_data(
                original_event, updated_data, latitude, longitude
            )
            
            # Save the updated event
            self.events[event_idx] = updated_event_data
            self.save_events()
            
            # Build success message
            changes_made = self._build_changes_list(event_without_images, updated_event_data, coordinates_updated)
            
            if changes_made:
                success_message = f"✅ Event {event_idx + 1} updated successfully!\n" + "\n".join(changes_made)
            else:
                success_message = f"✅ Event {event_idx + 1} data refreshed (no changes detected)"
            
            return True, success_message
            
        except Exception as e:
            return False, f"Error updating event: {str(e)}"
    
    def delete_event(self, event_idx: int) -> Tuple[bool, str]:
        """Delete an event and all its associated images."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            
            # Delete all associated image files
            for img_obj in event.get('images', []):
                local_path = img_obj.get('local_path')
                if local_path:
                    img_file = Path("data") / local_path
                    if img_file.exists():
                        img_file.unlink()
            
            # Delete the event
            self.events.pop(event_idx)
            self.save_events()
            
            return True, "Event and all images deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting event: {str(e)}"
    
    def update_event_checked_status(self, event_idx: int, checked: bool) -> None:
        """Update the checked status of an event."""
        if event_idx < len(self.events):
            self.events[event_idx]['checked'] = checked
            self.save_events()
    
    def add_image_to_event(self, event_idx: int, uploaded_file: Any, source_credit: str = "User Upload") -> Tuple[bool, str]:
        """Add an image to an event."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get("images", [])
            
            if len(images) >= MAX_IMAGES_PER_EVENT:
                return False, f"Maximum of {MAX_IMAGES_PER_EVENT} images allowed per event"
            
            # Generate filename
            img_index = get_next_available_image_index(images)
            file_extension = Path(uploaded_file.name).suffix
            final_filename = generate_image_filename(event, img_index, file_extension)
            
            # Determine save directory
            save_dir = self._get_save_directory(event_idx, images)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file
            save_path = save_dir / final_filename
            save_path.write_bytes(uploaded_file.getbuffer())
            
            # Create image object
            new_img_obj = create_image_object(
                local_path=str(save_path).replace("data\\", "").replace("data/", ""),
                filename=final_filename,
                source_credit=source_credit
            )
            
            # Add to event's images array
            if "images" not in event:
                event["images"] = []
            event["images"].append(new_img_obj)
            
            # Sort images by index
            sort_images_by_index(event["images"])
            
            # Update and save
            self.events[event_idx] = event
            self.save_events()
            
            return True, f"Successfully uploaded '{final_filename}'"
            
        except Exception as e:
            return False, f"Error uploading image: {str(e)}"
    
    def delete_image_from_event(self, event_idx: int, img_idx: int) -> Tuple[bool, str]:
        """Delete an image from an event."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get("images", [])
            
            if img_idx >= len(images):
                return False, "Image index out of range"
            
            img_obj = images[img_idx]
            
            # Delete the image file
            local_path = img_obj.get("local_path")
            if local_path:
                img_file = Path("data") / local_path
                if img_file.exists():
                    img_file.unlink()
            
            # Remove from array
            images.pop(img_idx)
            
            # Renumber images sequentially
            self._renumber_images_sequentially(event, event_idx)
            
            # Save changes to file
            self.save_events()
            
            return True, "Image deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting image: {str(e)}"
    
    def swap_with_thumbnail(self, event_idx: int, img_idx: int) -> Tuple[bool, str]:
        """Swap the selected image with the current thumbnail (index 1)."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get("images", [])
            
            if len(images) < 2 or img_idx >= len(images):
                return False, "Cannot swap: insufficient images"
            
            # Get the current thumbnail and selected image
            thumbnail_img = images[0]
            selected_img = images[img_idx]
            
            # Extract filenames and indexes
            thumbnail_filename = thumbnail_img.get('filename', '')
            selected_filename = selected_img.get('filename', '')
            
            if not thumbnail_filename or not selected_filename:
                return False, "Cannot swap: invalid filenames"
            
            # Extract indexes
            thumbnail_index = extract_image_index(thumbnail_filename)
            selected_index = extract_image_index(selected_filename)
            
            if thumbnail_index == 9999 or selected_index == 9999:
                return False, "Cannot swap: invalid index numbers in filenames"
            
            # Generate new filenames with swapped indexes
            thumbnail_stem = Path(thumbnail_filename).stem
            selected_stem = Path(selected_filename).stem
            thumbnail_ext = Path(thumbnail_filename).suffix
            selected_ext = Path(selected_filename).suffix
            
            # Create base filenames
            thumbnail_base = '_'.join(thumbnail_stem.split('_')[:-1])
            selected_base = '_'.join(selected_stem.split('_')[:-1])
            
            # Create new filenames
            new_thumbnail_filename = f"{selected_base}_{thumbnail_index}{selected_ext}"
            new_selected_filename = f"{thumbnail_base}_{selected_index}{thumbnail_ext}"
            
            # Get directory path
            thumbnail_local_path = thumbnail_img.get('local_path', '')
            if not thumbnail_local_path:
                return False, "Cannot swap: invalid local path"
            
            save_dir = Path("data") / Path(thumbnail_local_path).parent
            
            # Perform file swapping
            self._swap_image_files(
                save_dir, thumbnail_filename, selected_filename,
                new_thumbnail_filename, new_selected_filename,
                thumbnail_index, selected_index, thumbnail_ext, selected_ext
            )
            
            # Update image objects
            thumbnail_img['filename'] = new_thumbnail_filename
            thumbnail_img['local_path'] = str(save_dir / new_thumbnail_filename).replace("data\\", "").replace("data/", "")
            
            selected_img['filename'] = new_selected_filename
            selected_img['local_path'] = str(save_dir / new_selected_filename).replace("data\\", "").replace("data/", "")
            
            # Swap metadata (source_credit and original_url)
            thumbnail_source_credit = thumbnail_img.get('source_credit', '')
            thumbnail_original_url = thumbnail_img.get('original_url', '')
            selected_source_credit = selected_img.get('source_credit', '')
            selected_original_url = selected_img.get('original_url', '')
            
            thumbnail_img['source_credit'] = selected_source_credit
            thumbnail_img['original_url'] = selected_original_url
            selected_img['source_credit'] = thumbnail_source_credit
            selected_img['original_url'] = thumbnail_original_url
            
            # Swap positions in array
            images[0] = selected_img
            images[img_idx] = thumbnail_img
            
            # Sort images by index
            sort_images_by_index(images)
            
            # Update and save
            event["images"] = images
            self.events[event_idx] = event
            self.save_events()
            
            return True, "Successfully made image the new thumbnail!"
            
        except Exception as e:
            return False, f"Error swapping thumbnail: {str(e)}"
    
    def update_image_metadata(self, event_idx: int, img_idx: int, updated_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """Update image metadata."""
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get("images", [])
            
            if img_idx >= len(images):
                return False, "Image index out of range"
            
            # Update the image metadata
            images[img_idx].update(updated_metadata)
            
            # Save changes
            self.events[event_idx] = event
            self.save_events()
            
            return True, f"Image {img_idx + 1} metadata saved!"
            
        except Exception as e:
            return False, f"Error saving image metadata: {str(e)}"
    
    def _build_updated_event_data(self, original_event: Dict, updated_data: Dict, latitude: float, longitude: float) -> Dict:
        """Build updated event data in the correct order."""
        updated_event_data = {}
        
        # Process form values
        def process_form_value(key: str, form_value: Any, original_value: Any) -> Any:
            if isinstance(original_value, bool):
                return form_value
            elif isinstance(original_value, (int, float)):
                return form_value
            elif key == 'categories':
                return form_value
            elif key in ['start_datetime', 'end_datetime']:
                return form_value
            elif isinstance(original_value, list):
                try:
                    return json.loads(form_value) if form_value.strip() else []
                except json.JSONDecodeError:
                    return original_value
            elif isinstance(original_value, dict):
                try:
                    return json.loads(form_value) if form_value.strip() else {}
                except json.JSONDecodeError:
                    return original_value
            else:
                return form_value if form_value != "" else None
        
        # Build in correct order (same as original app.py)
        field_order = [
            'title', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
            'price_display', 'price', 'is_free', 'organiser', 'age_group_display',
            'min_age', 'max_age', 'datetime_display', 'start_datetime', 'end_datetime',
            'venue_name', 'categories', 'scraped_on', 'full_address', 'latitude', 'longitude'
        ]
        
        original_without_images = {k: v for k, v in original_event.items() if k != "images"}
        
        for field in field_order:
            if field in updated_data:
                updated_event_data[field] = process_form_value(field, updated_data[field], original_without_images.get(field))
            elif field == 'latitude':
                updated_event_data[field] = None if updated_data.get('full_address', '') == "" else latitude
            elif field == 'longitude':
                updated_event_data[field] = None if updated_data.get('full_address', '') == "" else longitude
            else:
                updated_event_data[field] = original_without_images.get(field)
        
        # Add any remaining fields not in the standard order
        for key, value in original_without_images.items():
            if key not in updated_event_data:
                if key in updated_data:
                    updated_event_data[key] = process_form_value(key, updated_data[key], value)
                else:
                    updated_event_data[key] = value
        
        # Add images and checked status
        updated_event_data["images"] = original_event.get("images", [])
        updated_event_data['checked'] = original_event.get('checked', False)
        
        return updated_event_data
    
    def _build_changes_list(self, original_event: Dict, updated_event: Dict, coordinates_updated: bool) -> List[str]:
        """Build a list of changes made to the event."""
        changes_made = []
        
        for key, new_value in updated_event.items():
            if key == "images":
                continue
            
            original_value = original_event.get(key)
            
            # Special handling for datetime fields
            if key in ['start_datetime', 'end_datetime']:
                orig_normalized = original_value
                new_normalized = new_value
                
                if orig_normalized and isinstance(orig_normalized, str):
                    if '+' in orig_normalized:
                        orig_normalized = orig_normalized.split('+')[0]
                    elif orig_normalized.endswith('Z'):
                        orig_normalized = orig_normalized[:-1]
                
                values_different = str(new_normalized) != str(orig_normalized)
            elif key in ['latitude', 'longitude']:
                orig_is_zero_or_null = (original_value == 0.0 or original_value == 0 or original_value is None)
                new_is_zero_or_null = (new_value == 0.0 or new_value == 0 or new_value is None)
                
                if orig_is_zero_or_null and new_is_zero_or_null:
                    values_different = False
                else:
                    values_different = str(new_value) != str(original_value)
            else:
                values_different = str(new_value) != str(original_value)
            
            if values_different:
                if key == 'latitude' and coordinates_updated:
                    continue
                elif key == 'longitude' and coordinates_updated:
                    continue
                else:
                    field_name = key.replace('_', ' ').title()
                    if isinstance(new_value, list):
                        if len(str(new_value)) > 50:
                            changes_made.append(f"📝 {field_name}: Updated")
                        else:
                            changes_made.append(f"📝 {field_name}: {new_value}")
                    elif isinstance(new_value, bool):
                        changes_made.append(f"📝 {field_name}: {'Yes' if new_value else 'No'}")
                    elif len(str(new_value)) > 50:
                        changes_made.append(f"📝 {field_name}: Updated")
                    else:
                        if key in ['latitude', 'longitude'] and new_value is None:
                            changes_made.append(f"📝 {field_name}: NULL")
                        else:
                            changes_made.append(f"📝 {field_name}: {new_value}")
        
        # Add coordinates update if address changed
        if coordinates_updated:
            changes_made.append(f"🌍 Coordinates: {updated_event.get('latitude', 0):.6f}, {updated_event.get('longitude', 0):.6f}")
        
        return changes_made
    
    def _get_save_directory(self, event_idx: int, images: List[Dict]) -> Path:
        """Get the directory to save images."""
        save_dir = EVENTS_OUTPUT_DIR
        
        # Try to use the same directory as existing images
        if images and images[0].get("local_path"):
            save_dir = Path("data") / Path(images[0]["local_path"]).parent
        else:
            # Check other events for directory structure
            for other_event in self.events:
                if other_event.get("images") and other_event["images"][0].get("local_path"):
                    example_path = Path(other_event["images"][0]["local_path"])
                    if len(example_path.parts) > 1:
                        # Use the full parent path, not just the first part
                        save_dir = Path("data") / example_path.parent
                    break
        
        return save_dir
    
    def _renumber_images_sequentially(self, event: Dict, event_idx: int) -> None:
        """Renumber all images in the event sequentially starting from 1."""
        images = event.get("images", [])
        if not images:
            return
        
        # Get event title for base filename
        event_title = event.get('title', 'untitled_event')
        base_filename = re.sub(r'[^a-zA-Z0-9]', '_', event_title)
        
        # Get directory path
        if images[0].get("local_path"):
            save_dir = Path("data") / Path(images[0]["local_path"]).parent
        else:
            save_dir = EVENTS_OUTPUT_DIR
        
        # Rename files sequentially
        temp_names = []
        for i, img in enumerate(images):
            old_filename = img.get('filename', '')
            if not old_filename:
                continue
            
            file_extension = Path(old_filename).suffix
            new_index = i + 1
            new_filename = f"{base_filename}_{new_index}{file_extension}"
            temp_filename = f"temp_rename_{i}_{new_index}{file_extension}"
            
            temp_names.append({
                'img': img,
                'old_filename': old_filename,
                'temp_filename': temp_filename,
                'new_filename': new_filename
            })
        
        # Two-pass renaming to avoid conflicts
        for item in temp_names:
            old_path = save_dir / item['old_filename']
            temp_path = save_dir / item['temp_filename']
            if temp_path.exists():
                temp_path.unlink()  # Remove the temp file if it already exists
            if old_path.exists():
                old_path.rename(temp_path)
        
        for item in temp_names:
            temp_path = save_dir / item['temp_filename']
            new_path = save_dir / item['new_filename']
            if temp_path.exists():
                temp_path.rename(new_path)
                item['img']['filename'] = item['new_filename']
                item['img']['local_path'] = str(new_path).replace("data\\", "").replace("data/", "")
    
    def _swap_image_files(self, save_dir: Path, old_thumb: str, old_selected: str, 
                         new_thumb: str, new_selected: str, thumb_idx: int, 
                         selected_idx: int, thumb_ext: str, selected_ext: str) -> None:
        """Perform the actual file swapping operation."""
        old_thumbnail_path = save_dir / old_thumb
        old_selected_path = save_dir / old_selected
        new_thumbnail_path = save_dir / new_thumb
        new_selected_path = save_dir / new_selected
        
        # Use temporary names to avoid conflicts
        temp_thumbnail_path = save_dir / f"temp_thumbnail_{thumb_idx}{thumb_ext}"
        temp_selected_path = save_dir / f"temp_selected_{selected_idx}{selected_ext}"
        
        # First pass: rename to temporary names
        if old_thumbnail_path.exists():
            old_thumbnail_path.rename(temp_thumbnail_path)
        if old_selected_path.exists():
            old_selected_path.rename(temp_selected_path)
        
        # Second pass: rename to final names
        if temp_thumbnail_path.exists():
            temp_thumbnail_path.rename(new_selected_path)
        if temp_selected_path.exists():
            temp_selected_path.rename(new_thumbnail_path) 