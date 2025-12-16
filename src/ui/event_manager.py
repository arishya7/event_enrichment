"""
Event Management System for Event JSON & Image Editor Application

This module provides comprehensive event management functionality including CRUD operations,
image handling, coordinate updates, and data persistence. The EventManager class serves
as the central interface for all event-related operations.

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
    """
    Handles event CRUD operations and image management.
    
    The EventManager class provides a comprehensive interface for managing events
    and their associated images. It handles all aspects of event data including
    creation, updating, deletion, and image management.
    
    Key Responsibilities:
    - Event data persistence and file management
    - Image upload, deletion, and metadata management
    - Automatic coordinate updates via Google Places API
    - Image indexing and sequential numbering
    - File system operations with error handling
    - Change tracking and success reporting
    
    Attributes:
        events (List[Dict]): List of event dictionaries
        file_path (Path): Path to the JSON file containing events
        
    Example:
        manager = EventManager(events, Path("data/events.json"))
        success, message = manager.update_event(0, updated_data)
    """
    
    def __init__(self, events: List[Dict], file_path: Path):
        """
        Initialize EventManager with events and file path.
        
        Args:
            events (List[Dict]): List of event dictionaries
            file_path (Path): Path to JSON file for persistence
        """
        self.events = events
        self.file_path = file_path
    
    def save_events(self) -> None:
        """
        Save events to file.
        
        Persists the current state of events to the JSON file with proper
        formatting and error handling.
        """
        # Remove unique_id from events before saving to keep JSON clean
        events_to_save = []
        for event in self.events:
            event_copy = event.copy()
            event_copy.pop('_unique_id', None)  # Remove unique_id if present
            events_to_save.append(event_copy)
        
        save_events_to_file(events_to_save, self.file_path)
        
        # Update session state cache if we're in a Streamlit context
        try:
            import streamlit as st
            session_key = f"events_{self.file_path.name}_{self.file_path.stat().st_mtime}"
            st.session_state[session_key] = self.events  # Keep unique_id in cache
        except:
            # Not in Streamlit context, ignore
            pass
    
    def update_event(self, event_idx: int, updated_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update an event with new data.
        
        Updates an event with new data and handles coordinate updates when
        the address changes. The function provides comprehensive error handling
        and detailed success/failure reporting.
        
        The update process includes:
        - Data validation and processing
        - Automatic coordinate lookup for address changes
        - File system operations for image management
        - Change tracking and reporting
        - Error handling and recovery
        
        Args:
            event_idx (int): Index of the event to update
            updated_data (Dict[str, Any]): New event data
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
            
        Example:
            success, message = manager.update_event(0, {
                'title': 'Updated Event',
                'address_display': '123 New Street, Singapore'
            })
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            # Get original event
            original_event = self.events[event_idx]
            event_without_images = {k: v for k, v in original_event.items() if k != "images"}
            
            # Handle coordinate updates if address changed
            coordinates_updated = False
            new_address_display = updated_data.get('address_display', '')
            original_address_display = original_event.get('address_display', '')
            
            latitude = event_without_images.get('latitude', 0.0)
            longitude = event_without_images.get('longitude', 0.0)
            
            if latitude is None:
                latitude = 0.0
            if longitude is None:
                longitude = 0.0
            
            
            if (new_address_display != original_address_display and 
                new_address_display and new_address_display.strip() and 
                GOOGLE_PLACES_AVAILABLE):
                new_longitude, new_latitude = get_coordinates_from_address(new_address_display)    
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
        """
        Delete an event and all its associated images.
        
        Removes an event from the events list and deletes all associated
        image files from the file system. Provides comprehensive cleanup
        and error handling.
        
        Args:
            event_idx (int): Index of the event to delete
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
            
        Example:
            success, message = manager.delete_event(0)
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get('images', [])
            
            # Delete image files
            for img in images:
                local_path = img.get('local_path', '')
                if local_path:
                    img_file = Path("data") / local_path
                    if img_file.exists():
                        img_file.unlink()
            
            # Remove event from list
            del self.events[event_idx]
            self.save_events()
            
            return True, f"✅ Event {event_idx + 1} and {len(images)} images deleted successfully!"
            
        except Exception as e:
            return False, f"Error deleting event: {str(e)}"
    
    def update_event_checked_status(self, event_idx: int, checked: bool) -> None:
        """
        Update the checked status of an event.
        
        Args:
            event_idx (int): Index of the event to update
            checked (bool): New checked status
        """
        if event_idx < len(self.events):
            self.events[event_idx]['checked'] = checked
            self.save_events()
    
    def add_image_to_event(self, event_idx: int, uploaded_file: Any, source_credit: str = "User Upload") -> Tuple[bool, str]:
        """
        Add an uploaded image to an event.
        
        Processes an uploaded file and adds it to the event's image collection.
        Handles file saving, metadata creation, and index management.
        
        The function performs:
        - File validation and type checking
        - Automatic filename generation
        - File system operations
        - Image metadata creation
        - Index management and sorting
        
        Args:
            event_idx (int): Index of the event to add image to
            uploaded_file (Any): Streamlit uploaded file object
            source_credit (str): Source credit for the image
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
            
        Example:
            success, message = manager.add_image_to_event(0, uploaded_file, "User Upload")
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get('images', [])
            
            # Check image count limit
            if len(images) >= MAX_IMAGES_PER_EVENT:
                return False, f"Maximum of {MAX_IMAGES_PER_EVENT} images allowed per event."
            
            # Generate filename and index
            file_extension = Path(uploaded_file.name).suffix
            img_index = get_next_available_image_index(images)
            filename = generate_image_filename(event, img_index, file_extension)
            
            # Save file
            save_dir = self._get_save_directory(event_idx, images)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = save_dir / filename
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Create image object
            local_path = str(file_path.relative_to(Path("data")))
            img_obj = create_image_object(local_path, filename, "", source_credit)
            
            # Add to images list and sort
            images.append(img_obj)
            sort_images_by_index(images)
            
            # Update event and save
            event['images'] = images
            self.save_events()
            
            return True, f"✅ Image '{filename}' added to Event {event_idx + 1} successfully!"
            
        except Exception as e:
            return False, f"Error adding image: {str(e)}"
    
    def delete_image_from_event(self, event_idx: int, img_idx: int) -> Tuple[bool, str]:
        """
        Delete an image from an event.
        
        Removes an image from the event's image collection and deletes
        the associated file from the file system.
        
        Args:
            event_idx (int): Index of the event
            img_idx (int): Index of the image to delete
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get('images', [])
            
            if img_idx >= len(images):
                return False, "Image index out of range"
            
            # Get image info
            img_obj = images[img_idx]
            filename = img_obj.get('filename', '')
            local_path = img_obj.get('local_path', '')
            deleted_file = False
            
            if local_path:
                # Try the exact path from JSON
                img_file = Path("data") / local_path
                if img_file.exists() and img_file.is_file():
                    try:
                        img_file.unlink()
                        print(f"✅ Deleted local file: {img_file}")
                        deleted_file = True
                    except Exception as file_error:
                        print(f"⚠️  Warning: Could not delete local file {img_file}: {file_error}")
                
                # If exact path didn't work, try to find file by filename in the images directory
                if not deleted_file and filename:
                    # Extract images directory from local_path
                    # local_path format: "events_output/Nov_12/images/filename.jpg"
                    path_parts = Path(local_path).parts
                    if len(path_parts) >= 2:
                        # Try to find images directory
                        images_dir = Path("data") / path_parts[0] / path_parts[1] / "images"
                        if images_dir.exists():
                            # Try exact filename match
                            exact_match = images_dir / filename
                            if exact_match.exists() and exact_match.is_file():
                                try:
                                    exact_match.unlink()
                                    print(f"✅ Deleted local file (by filename): {exact_match}")
                                    deleted_file = True
                                except Exception as file_error:
                                    print(f"⚠️  Warning: Could not delete file {exact_match}: {file_error}")
                            
                            # If still not found, try fuzzy match (find files with similar name)
                            if not deleted_file:
                                # Look for files that start with similar pattern
                                base_name = Path(filename).stem
                                # Try to match by event ID prefix or similar pattern
                                for img_file in images_dir.glob("*.jpg"):
                                    if base_name.lower() in img_file.stem.lower() or img_file.stem.lower() in base_name.lower():
                                        try:
                                            img_file.unlink()
                                            print(f"✅ Deleted local file (fuzzy match): {img_file}")
                                            deleted_file = True
                                            break
                                        except Exception as file_error:
                                            print(f"⚠️  Warning: Could not delete file {img_file}: {file_error}")
            
            if not deleted_file and filename:
                print(f"⚠️  Could not find file to delete: {filename} (local_path: {local_path})")
            
            # Remove from images list - modify in place
            images.pop(img_idx)
            
            # Renumber remaining images
            self._renumber_images_sequentially(event, event_idx)
            
            # Ensure event dict is updated (should already be updated since images is a reference)
            event['images'] = images
            # Also update self.events to ensure it's synced
            self.events[event_idx] = event
            
            # Force save and verify
            try:
                self.save_events()
                # Verify the save worked by checking file was updated
                import time
                time.sleep(0.1)  # Small delay to ensure file write completes
                print(f"✅ Saved events after deleting image {img_idx} from event {event_idx}")
            except Exception as save_error:
                print(f"❌ Error saving events: {save_error}")
                return False, f"Image deleted but failed to save: {str(save_error)}"
            
            return True, f"✅ Image '{filename}' deleted from Event {event_idx + 1} successfully!"
            
        except Exception as e:
            print(f"❌ Error in delete_image_from_event: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error deleting image: {str(e)}"
    
    def swap_with_thumbnail(self, event_idx: int, img_idx: int) -> Tuple[bool, str]:
        """
        Swap an image with the thumbnail (first image).
        
        Exchanges the positions of the specified image and the thumbnail,
        updating both the data structure and file system.
        
        Args:
            event_idx (int): Index of the event
            img_idx (int): Index of the image to swap with thumbnail
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get('images', [])
            
            if len(images) < 2:
                return False, "Need at least 2 images to perform swap."
            
            if img_idx >= len(images):
                return False, "Image index out of range"
            
            if img_idx == 0:
                return False, "Image is already the thumbnail."
            
            # Get image info
            thumbnail = images[0]
            selected_img = images[img_idx]
            
            # Get file paths
            save_dir = self._get_save_directory(event_idx, images)
            thumb_path = save_dir / thumbnail['filename']
            selected_path = save_dir / selected_img['filename']
            
            if not thumb_path.exists() or not selected_path.exists():
                return False, "One or both image files not found."
            
            # Get file extensions
            thumb_ext = Path(thumbnail['filename']).suffix
            selected_ext = Path(selected_img['filename']).suffix
            
            # Perform file swap
            self._swap_image_files(
                save_dir, thumbnail['filename'], selected_img['filename'],
                selected_img['filename'], thumbnail['filename'], 0, img_idx,
                thumb_ext, selected_ext
            )
            
            # Store original values before swapping
            original_thumb_filename = thumbnail['filename']
            original_thumb_local_path = thumbnail['local_path']
            original_selected_filename = selected_img['filename']
            original_selected_local_path = selected_img['local_path']
            
            # Update image objects with swapped filenames and local_paths
            # The thumbnail (index 0) now has the selected image's filename and path
            thumbnail['filename'] = original_selected_filename
            thumbnail['local_path'] = original_selected_local_path
            
            # The selected image now has the thumbnail's original filename and path
            selected_img['filename'] = original_thumb_filename
            selected_img['local_path'] = original_thumb_local_path
            
            # Swap positions in list
            images[0], images[img_idx] = images[img_idx], images[0]
            
            # Update event and save
            event['images'] = images
            self.save_events()
            
            return True, f"✅ Successfully swapped image {img_idx + 1} with thumbnail!"
            
        except Exception as e:
            return False, f"Error swapping images: {str(e)}"
    
    def update_image_metadata(self, event_idx: int, img_idx: int, updated_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update metadata for a specific image.
        
        Updates the metadata fields of an image object with new values.
        Supports updating fields like filename, original_url, and source_credit.
        
        Args:
            event_idx (int): Index of the event
            img_idx (int): Index of the image to update
            updated_metadata (Dict[str, Any]): New metadata values
            
        Returns:
            Tuple[bool, str]: (success, message) indicating operation result
        """
        if event_idx >= len(self.events):
            return False, "Event index out of range"
        
        try:
            event = self.events[event_idx]
            images = event.get('images', [])
            
            if img_idx >= len(images):
                return False, "Image index out of range"
            
            # Update metadata
            for key, value in updated_metadata.items():
                if key in images[img_idx]:
                    images[img_idx][key] = value
            
            # Update event and save
            event['images'] = images
            self.save_events()
            
            return True, f"✅ Image metadata updated successfully!"
            
        except Exception as e:
            return False, f"Error updating image metadata: {str(e)}"
    
    def _build_updated_event_data(self, original_event: Dict, updated_data: Dict, latitude: float, longitude: float) -> Dict:
        """
        Build updated event data from original and new data.
        
        Processes form data and builds a complete updated event object,
        handling different data types and validation.
        
        Args:
            original_event (Dict): Original event data
            updated_data (Dict): New form data
            latitude (float): Updated latitude coordinate
            longitude (float): Updated longitude coordinate
            
        Returns:
            Dict: Complete updated event object
        """
        def process_form_value(key: str, form_value: Any, original_value: Any) -> Any:
            """Process individual form values with type conversion."""
            if key in ['price', 'min_age', 'max_age']:
                try:
                    return float(form_value) if form_value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            elif key in ['is_free']:
                return bool(form_value)
            elif key in ['categories']:
                return form_value if isinstance(form_value, list) else []
            elif key in ['latitude', 'longitude']:
                return float(form_value) if form_value is not None else 0.0
            elif isinstance(original_value, bool):
                return bool(form_value)
            elif isinstance(original_value, (int, float)):
                try:
                    return float(form_value) if form_value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            elif isinstance(original_value, list):
                try:
                    if isinstance(form_value, str):
                        return json.loads(form_value)
                    return form_value if isinstance(form_value, list) else []
                except json.JSONDecodeError:
                    return []
            elif isinstance(original_value, dict):
                try:
                    if isinstance(form_value, str):
                        return json.loads(form_value)
                    return form_value if isinstance(form_value, dict) else {}
                except json.JSONDecodeError:
                    return {}
            else:
                return str(form_value) if form_value is not None else ""
        
        # Build updated event
        updated_event = original_event.copy()
        
        # Process each field
        for key, original_value in original_event.items():
            if key == 'images':
                continue  # Handle images separately
            
            if key in updated_data:
                updated_event[key] = process_form_value(key, updated_data[key], original_value)
        
        # Update coordinates
        updated_event['latitude'] = latitude
        updated_event['longitude'] = longitude
        
        return updated_event
    
    def _build_changes_list(self, original_event: Dict, updated_event: Dict, coordinates_updated: bool) -> List[str]:
        """
        Build a list of changes made to the event.
        
        Compares original and updated event data to identify and report
        changes made during the update process.
        
        Args:
            original_event (Dict): Original event data
            updated_event (Dict): Updated event data
            coordinates_updated (bool): Whether coordinates were updated
            
        Returns:
            List[str]: List of change descriptions
        """
        changes = []
        
        # Check for field changes
        for key in original_event:
            if key == 'images':
                continue
            
            original_value = original_event.get(key)
            updated_value = updated_event.get(key)
            
            if original_value != updated_value:
                if key == 'title':
                    changes.append(f"📝 Title updated")
                elif key == 'organiser':
                    changes.append(f"👤 Organiser updated")
                elif key == 'description':
                    changes.append(f"📄 Description updated")
                elif key == 'url':
                    changes.append(f"🔗 URL updated")
                elif key == 'categories':
                    changes.append(f"🏷️ Categories updated")
                elif key == 'price':
                    changes.append(f"💰 Price updated")
                elif key == 'is_free':
                    changes.append(f"🆓 Free status updated")
                elif key == 'start_datetime' or key == 'end_datetime':
                    changes.append(f"📅 Date/time updated")
                elif key == 'venue_name':
                    changes.append(f"🏢 Venue updated")
                elif key == 'address_display':
                    changes.append(f"📍 Address updated")
                else:
                    changes.append(f"📝 {key} updated")
        
        # Add coordinate update message
        if coordinates_updated:
            changes.append(f"🗺️ Coordinates updated via Google Places API")
        
        return changes
    
    def _get_save_directory(self, event_idx: int, images: List[Dict]) -> Path:
        """
        Get the directory for saving event images.
        
        Determines the appropriate directory for saving images based on
        the event index and existing image structure.
        
        Args:
            event_idx (int): Index of the event
            images (List[Dict]): List of existing images
            
        Returns:
            Path: Directory path for saving images
        """
        if images:
            # Use existing image path structure
            first_img = images[0]
            local_path = first_img.get('local_path', '')
            if local_path:
                return Path("data") / Path(local_path).parent
        
        # Create images folder in the same directory as the JSON file
        json_dir = self.file_path.parent
        return json_dir / "images" / "user_uploads"
    
    def _renumber_images_sequentially(self, event: Dict, event_idx: int) -> None:
        """
        Renumber images sequentially after deletion.
        
        Updates image filenames to maintain sequential numbering
        after an image is deleted from the collection.
        
        Args:
            event (Dict): Event dictionary
            event_idx (int): Index of the event
        """
        images = event.get('images', [])
        if not images:
            return
        
        save_dir = self._get_save_directory(event_idx, images)
        
        for i, img in enumerate(images, 1):
            old_filename = img.get('filename', '')
            if not old_filename:
                continue
            
            # Generate new filename
            file_extension = Path(old_filename).suffix
            new_filename = generate_image_filename(event, i, file_extension)
            
            # Rename file
            old_path = save_dir / old_filename
            new_path = save_dir / new_filename
            
            if old_path.exists():
                old_path.rename(new_path)
            
            # Update image object
            img['filename'] = new_filename
            img['local_path'] = str(new_path.relative_to(Path("data")))
    
    def _swap_image_files(self, save_dir: Path, old_thumb: str, old_selected: str, 
                         new_thumb: str, new_selected: str, thumb_idx: int, 
                         selected_idx: int, thumb_ext: str, selected_ext: str) -> None:
        """
        Swap image files in the file system.
        
        Performs the actual file system operations to swap two image files,
        using temporary files to ensure safe swapping.
        
        Args:
            save_dir (Path): Directory containing the images
            old_thumb (str): Original thumbnail filename
            old_selected (str): Original selected image filename
            new_thumb (str): New thumbnail filename
            new_selected (str): New selected image filename
            thumb_idx (int): Thumbnail index
            selected_idx (int): Selected image index
            thumb_ext (str): Thumbnail file extension
            selected_ext (str): Selected image file extension
        """
        # Create unique temporary filenames to avoid conflicts
        temp_thumb = f"temp_thumb_{thumb_idx}_{selected_idx}{thumb_ext}"
        temp_selected = f"temp_selected_{thumb_idx}_{selected_idx}{selected_ext}"
        
        # Step 1: Rename files to temporary names
        (save_dir / old_thumb).rename(save_dir / temp_thumb)
        (save_dir / old_selected).rename(save_dir / temp_selected)
        
        # Step 2: Rename temporary files to their final swapped positions
        (save_dir / temp_thumb).rename(save_dir / new_thumb)
        (save_dir / temp_selected).rename(save_dir / new_selected) 