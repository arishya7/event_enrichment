"""
Main application logic for the Event JSON & Image Editor.
"""

import sys
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any
import argparse
import time

# Add the project root to the Python path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from src.ui.constants import (
    STREAMLIT_PAGE_CONFIG, DEFAULT_EVENTS_PER_PAGE,
    DEFAULT_ASPECT_RATIO, MAX_IMAGES_PER_EVENT, SUPPORTED_IMAGE_TYPES
)
from src.ui.helpers import (
    find_timestamp_folders, find_json_files_in_timestamp, load_events_from_file,
    calculate_pagination
)
from src.ui.components import (
    render_aspect_ratio_selector, render_event_header, render_event_form,
    render_image_upload_section, render_success_message, render_page_header,
    display_image_with_aspect_ratio, render_search_section
)
from src.ui.event_manager import EventManager


def initialize_session_state():
    """Initialize session state variables."""
    if 'deleted_image_slot' not in st.session_state:
        st.session_state['deleted_image_slot'] = None
    
    if 'delete_event_idx' not in st.session_state:
        st.session_state['delete_event_idx'] = None
    
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 0
    
    if 'events_per_page' not in st.session_state:
        st.session_state['events_per_page'] = DEFAULT_EVENTS_PER_PAGE
    
    if 'aspect_ratio' not in st.session_state:
        st.session_state['aspect_ratio'] = DEFAULT_ASPECT_RATIO
    
    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = ""
    
    if 'case_sensitive_search' not in st.session_state:
        st.session_state['case_sensitive_search'] = False


@st.dialog("Delete Event Confirmation")
def confirm_delete_event(event_manager: EventManager, event_idx: int, event: Dict):
    """Show confirmation dialog for event deletion."""
    st.write("Are you sure you want to delete this event and all its images?")
    st.write(f"**Event:** {event.get('title', 'Untitled Event')}")
    st.write(f"**Images to delete:** {len(event.get('images', []))}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            success, message = event_manager.delete_event(event_idx)
            if success:
                # Update pagination after deletion
                update_pagination_after_deletion(len(event_manager.events))
                st.success(message)
            else:
                st.error(message)
            st.rerun()
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Delete Image Confirmation")
def confirm_delete_image(event_manager: EventManager, event_idx: int, img_idx: int, img_obj: Dict):
    """Show confirmation dialog for image deletion."""
    st.write("Are you sure you want to delete this image?")
    
    # Show image preview if available
    local_path = "data\\" + img_obj.get("local_path", "")
    if local_path:
        img_file = Path(local_path)
        if img_file.exists():
            current_aspect_ratio = st.session_state.get('aspect_ratio', DEFAULT_ASPECT_RATIO)
            display_image_with_aspect_ratio(str(img_file), current_aspect_ratio, 300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            success, message = event_manager.delete_image_from_event(event_idx, img_idx)
            if success:
                st.success(message)
            else:
                st.error(message)
                time.sleep(3)

            st.rerun()
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def update_pagination_after_deletion(new_total: int):
    """Update pagination state after event deletion."""
    events_per_page = st.session_state['events_per_page']
    new_total_pages = (new_total + events_per_page - 1) // events_per_page if new_total > 0 else 0
    
    # If current page is now beyond the last page, go to the last page
    if st.session_state['current_page'] >= new_total_pages and new_total_pages > 0:
        st.session_state['current_page'] = new_total_pages - 1
    elif new_total == 0:
        st.session_state['current_page'] = 0


def render_image_section(event_manager: EventManager, event: Dict, event_idx: int):
    """Render the image management section for an event."""
    images = event.get("images", [])
    current_image_count = len(images)
    
    if not images:
        st.info(f"No images found for Event {event_idx + 1}.")
        
        # Add new images section when no images exist
        st.markdown("### 📁 Add New Images")
        uploaded_file = render_image_upload_section(event_idx, current_image_count, "_new")
        
        if uploaded_file:
            success, message = event_manager.add_image_to_event(event_idx, uploaded_file)
            if success:
                st.success(f"✅ {message} to Event {event_idx + 1}!")
                st.rerun()
            else:
                st.error(f"❌ {message}")
    else:
        # Display existing images
        img_idx = 0
        while img_idx < len(images):
            img_obj = images[img_idx]
            st.markdown(f"### Image {img_idx + 1}")
            
            local_path = "data\\" + img_obj.get("local_path", "")
            if not local_path:
                img_idx += 1
                continue
            
            img_file = Path(local_path)
            img_col, meta_col = st.columns([4, 3])
            
            with img_col:
                if img_file.exists():
                    current_aspect_ratio = st.session_state.get('aspect_ratio', DEFAULT_ASPECT_RATIO)
                    display_image_with_aspect_ratio(str(img_file), current_aspect_ratio, 1000)
                else:
                    st.warning(f"Image not found: {img_file}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Thumbnail controls
                if img_idx == 0:
                    st.info("🖼️ This is the thumbnail image", icon="📌")
                else:
                    if st.button(f"📌 Make Thumbnail", key=f"thumbnail_btn_{event_idx}_{img_idx}", 
                               use_container_width=True, type='secondary'):
                        success, message = event_manager.swap_with_thumbnail(event_idx, img_idx)
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                
                # Delete button
                if st.button(f"🗑️ Delete Image", key=f"delete_btn_{event_idx}_{img_idx}", 
                           use_container_width=True, type='primary'):
                    confirm_delete_image(event_manager, event_idx, img_idx, img_obj)
                
                st.markdown("<br>", unsafe_allow_html=True)
            
            with meta_col:
                render_image_metadata_form(event_manager, event_idx, img_idx, img_obj)
            
            st.divider()
            img_idx += 1
        
        # Add section to upload additional images
        st.markdown("### ➕ Add More Images")
        additional_file = render_image_upload_section(event_idx, current_image_count, "_additional")
        
        if additional_file:
            success, message = event_manager.add_image_to_event(event_idx, additional_file)
            if success:
                st.success(f"✅ {message} to Event {event_idx + 1}!")
                st.rerun()
            else:
                st.error(f"❌ {message}")


def render_image_metadata_form(event_manager: EventManager, event_idx: int, img_idx: int, img_obj: Dict):
    """Render the image metadata editing form."""
    with st.form(key=f"img_form_{event_idx}_{img_idx}"):
        st.markdown("**📝 Image Metadata**")
        
        # File uploader for replacing image
        new_img_file = st.file_uploader(
            "Replace image file (optional)",
            type=SUPPORTED_IMAGE_TYPES,
            key=f"replace_img_upload_{event_idx}_{img_idx}",
            help="Upload a new image to replace the current one. The filename will be kept but extension will be updated."
        )
        
        # Metadata fields
        metadata_updates = {}
        
        metadata_updates['filename'] = st.text_input(
            "Filename",
            value=img_obj.get('filename', ''),
            key=f"img_filename_{event_idx}_{img_idx}",
            disabled=True
        )
        
        metadata_updates['local_path'] = st.text_input(
            "Local Path",
            value=img_obj.get('local_path', ''),
            help="Path to the image file",
            key=f"img_local_path_{event_idx}_{img_idx}",
            disabled=True
        )
        
        metadata_updates['original_url'] = st.text_input(
            "Original URL",
            value=img_obj.get('original_url', ''),
            help="URL where the image was originally found",
            key=f"img_original_url_{event_idx}_{img_idx}"
        )
        
        metadata_updates['source_credit'] = st.text_input(
            "Source Credit",
            value=img_obj.get('source_credit', ''),
            help="Credit or attribution for the image source",
            key=f"img_source_credit_{event_idx}_{img_idx}"
        )
        
        # Handle additional fields
        for key, value in img_obj.items():
            if key not in ['filename', 'local_path', 'original_url', 'source_credit']:
                if isinstance(value, str):
                    metadata_updates[key] = st.text_input(
                        key.replace('_', ' ').title(),
                        value=value,
                        key=f"img_{key}_{event_idx}_{img_idx}"
                    )
                elif isinstance(value, (int, float)):
                    metadata_updates[key] = st.number_input(
                        key.replace('_', ' ').title(),
                        value=float(value),
                        key=f"img_{key}_{event_idx}_{img_idx}"
                    )
                elif isinstance(value, bool):
                    metadata_updates[key] = st.checkbox(
                        key.replace('_', ' ').title(),
                        value=value,
                        key=f"img_{key}_{event_idx}_{img_idx}"
                    )
                else:
                    import json
                    metadata_updates[key] = st.text_area(
                        key.replace('_', ' ').title(),
                        value=json.dumps(value, indent=2, ensure_ascii=False) if value else "",
                        height=60,
                        key=f"img_{key}_{event_idx}_{img_idx}"
                    )
        
        # Form submit button
        if st.form_submit_button("💾 Save Image", type="primary"):
            # Handle image replacement if uploaded
            if new_img_file:
                # Get the current image file path
                current_local_path = img_obj.get('local_path', '')
                if current_local_path:
                    image_file_path = Path("data") / current_local_path
                    # Overwrite the file with the new uploaded file
                    image_file_path.write_bytes(new_img_file.getbuffer())
            
            success, message = event_manager.update_image_metadata(event_idx, img_idx, metadata_updates)
            if success:
                st.success(f"✅ {message}")
                st.rerun()
            else:
                st.error(f"❌ {message}")


def get_events_output_dir() -> Path:
    """Parse command line arguments to get events output directory."""
    parser = argparse.ArgumentParser(description='Event JSON & Image Editor')
    parser.add_argument('--events-output', 
                       type=str, 
                       help='Path to events output directory',
                       default='data/events_output')
    
    # Parse known args to handle Streamlit's own arguments
    args, unknown = parser.parse_known_args()
    
    return Path(args.events_output)


def main():
    """Main application function."""
    # Set page config
    st.set_page_config(**STREAMLIT_PAGE_CONFIG)
    
    # Initialize session state
    initialize_session_state()
    
    # Get events output directory from command line arguments
    events_output_dir = get_events_output_dir()
    
    st.title("Event JSON & Image Editor")
    st.info(f"📁 Events directory: {events_output_dir.absolute()}")
    st.divider()
    
    # 1. Select timestamp folder and aspect ratio
    timestamp_folders = find_timestamp_folders(events_output_dir)
    if not timestamp_folders:
        st.warning(f"No timestamp folders found in {events_output_dir}.")
        st.stop()
    
    # Three-column layout for controls
    col1, col2, col3 = st.columns([1, 3, 3])
    
    with col1:
        aspect_ratio = render_aspect_ratio_selector()
        st.session_state['aspect_ratio'] = aspect_ratio
    
    with col2:
        selected_timestamp_folder = st.selectbox(
            "Select the timestamp:",
            timestamp_folders,
            format_func=lambda p: p.name,
            help="Select the timestamp folder containing the events you want to edit"
        )
    
    # 2. Select JSON file within the selected timestamp folder
    json_files_in_timestamp = find_json_files_in_timestamp(selected_timestamp_folder)
    if not json_files_in_timestamp:
        st.warning(f"No JSON files found in folder {selected_timestamp_folder.name}.")
        st.stop()
    
    with col3:
        selected_file = st.selectbox(
            "Select an event JSON file to edit:",
            json_files_in_timestamp,
            format_func=lambda p: p.name,
            help="Select the JSON file containing the events you want to edit"
        )
    
    # 3. Load events and create event manager
    try:
        events = load_events_from_file(selected_file)
        event_manager = EventManager(events, selected_file)
    except Exception as e:
        st.error(f"Failed to load events: {e}")
        st.stop()
    
    # 4. Search functionality
    search_term = st.session_state.get('search_term', '')
    case_sensitive = st.session_state.get('case_sensitive_search', False)
    
    new_search_term, new_case_sensitive, filtered_events = render_search_section(
        events, search_term, case_sensitive
    )
    
    # Update session state if search parameters changed
    if new_search_term != search_term or new_case_sensitive != case_sensitive:
        st.session_state['search_term'] = new_search_term
        st.session_state['case_sensitive_search'] = new_case_sensitive
        st.session_state['current_page'] = 0  # Reset to first page when searching
        st.rerun()
    
    # 5. Calculate pagination for filtered events
    total_events = len(filtered_events)
    events_per_page = st.session_state['events_per_page']
    current_page = st.session_state['current_page']
    
    pagination_info = calculate_pagination(total_events, events_per_page, current_page)
    
    # Update session state with corrected page
    st.session_state['current_page'] = pagination_info['current_page']
    
    # 6. Display header with pagination
    render_page_header(pagination_info)
    
    # 7. Display events for current page
    start_idx = pagination_info['start_idx']
    end_idx = pagination_info['end_idx']
    current_page_events = filtered_events[start_idx:end_idx]
    
    for page_event_idx, event in enumerate(current_page_events):
        # Calculate actual event index in the full list
        # Find the original index of this event in the full events list
        original_event_idx = events.index(event)
        
        # Event separator
        st.markdown(
            """
            <hr style="
                border: none;
                border-top: 10px solid white; 
                text-align: center;
                margin-left: auto;
                margin-right: auto;
                width: 100%; 
            ">
            """,
            unsafe_allow_html=True
        )
        
        # Event header with checkbox and delete button
        current_checked = event.get('checked', False)
        new_checked, delete_requested = render_event_header(original_event_idx, current_checked)
        
        # Update checked status if changed
        if new_checked != current_checked:
            event_manager.update_event_checked_status(original_event_idx, new_checked)
            st.rerun()
        
        # Handle delete request
        if delete_requested:
            confirm_delete_event(event_manager, original_event_idx, event)
        
        # Show form and images only for unchecked events
        if not new_checked:
            # Event form
            form_data = render_event_form(event, original_event_idx)
            if form_data:
                success, message = event_manager.update_event(original_event_idx, form_data)
                if success:
                    st.session_state[f'success_message_{original_event_idx}'] = message
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            
            # Show success message
            render_success_message(original_event_idx)
            
            # Image management section
            render_image_section(event_manager, event, original_event_idx)


if __name__ == "__main__":
    main() 