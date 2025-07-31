"""
UI Components for Event JSON & Image Editor Application

This module provides reusable UI components and widgets for the Event JSON & Image Editor
application. It contains all the visual elements and interactive components used throughout
the application interface.

"""

import base64
import streamlit as st
from pathlib import Path
from datetime import date, time
from typing import Dict, List, Any, Optional, Tuple

from src.ui.constants import (
    AVAILABLE_CATEGORIES, ACTIVITY_OR_EVENT, SPECIAL_FIELDS, DISABLED_FIELDS,
    ASPECT_RATIOS, IMAGE_DISPLAY_BASE_WIDTH, THUMBNAIL_PREVIEW_WIDTH,
    SUPPORTED_IMAGE_TYPES, MAX_IMAGES_PER_EVENT
)
from src.ui.helpers import (
    get_image_display_params, parse_iso_datetime, combine_to_iso_datetime,
    validate_image_count, calculate_pagination, filter_events_by_search
)

import os
from PIL import Image, UnidentifiedImageError


def display_image_with_aspect_ratio(image_path: str, aspect_ratio: str = "Original", base_width: int = IMAGE_DISPLAY_BASE_WIDTH) -> None:
    """
    Display an image with the specified aspect ratio.
    
    Renders an image with precise aspect ratio control using either CSS styling
    or native Streamlit image display. Supports multiple image formats and
    provides fallback handling for various error conditions.
    
    The function provides:
    - CSS-based aspect ratio control for consistent display
    - Automatic image format detection and MIME type handling
    - Base64 encoding for HTML display
    - Fallback to native Streamlit display for original aspect ratio
    - Comprehensive error handling for missing or corrupted files
    
    Args:
        image_path (str): Path to the image file
        aspect_ratio (str): Aspect ratio to apply ("Original", "4:3", "16:9")
        base_width (int): Base width for image display calculations
        
    Example:
        display_image_with_aspect_ratio("event_image.jpg", "16:9", 800)
    """
    params = get_image_display_params(aspect_ratio, base_width)
    if params["css_style"]:
        # Use HTML/CSS for aspect ratio control
        try:
            # Read and encode image
            with open(image_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
            
            # Determine image format
            img_format = Path(image_path).suffix.lower()
            if img_format in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif img_format == '.png':
                mime_type = 'image/png'
            elif img_format == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/jpeg'  # default
            
            # Create HTML with styled image (no caption)
            html_content = f"""
            <div style="text-align: center; margin: 10px 0;">
                <img src="data:{mime_type};base64,{img_data}" 
                     style="{params['css_style']}" 
                     alt="">
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Cannot display image: {image_path} ({e})")
            try:
                st.image(image_path, width=params["width"], use_container_width=params["use_container_width"])
            except (UnidentifiedImageError, FileNotFoundError, OSError):
                pass  # Already handled above
    else:
        # Use regular st.image for original aspect ratio (no caption)
        try:
            st.image(image_path, width=params["width"], use_container_width=params["use_container_width"])
        except (UnidentifiedImageError, FileNotFoundError, OSError) as e:
            st.warning(f"Cannot display image: {image_path} ({e})")
            
def render_aspect_ratio_selector() -> str:
    """
    Render the aspect ratio selector dropdown.
    
    Creates a dropdown widget for selecting image display aspect ratios.
    Provides user-friendly options with helpful descriptions.
    
    Returns:
        str: Selected aspect ratio value
        
    Example:
        selected_ratio = render_aspect_ratio_selector()
        # Returns: "16:9", "4:3", or "Original"
    """
    return st.selectbox(
        "Aspect Ratio 📷",
        options=ASPECT_RATIOS,
        index=0,
        help="Select how images should be displayed"
    )


def render_pagination_controls(pagination_info: Dict[str, int]) -> Optional[int]:
    """
    Render pagination controls and return selected page if changed.
    
    Creates a pagination interface with previous/next buttons and a page selector.
    Handles edge cases like single-page results and provides intuitive navigation.
    
    Args:
        pagination_info (Dict[str, int]): Pagination information containing:
            - total_pages: Total number of pages
            - current_page: Current page number
            
    Returns:
        Optional[int]: New page number if changed, None otherwise
        
    Example:
        new_page = render_pagination_controls(pagination_info)
        if new_page is not None:
            # Handle page change
    """
    total_pages = pagination_info["total_pages"]
    current_page = pagination_info["current_page"]
    
    if total_pages <= 1:
        return None
    
    col_prev, col_page, col_next = st.columns([1, 3, 1])
    
    with col_prev:
        if st.button("◀ Prev", disabled=current_page == 0):
            return max(0, current_page - 1)
    
    with col_page:
        selected_page = st.selectbox(
            "Page",
            options=range(total_pages),
            index=current_page,
            format_func=lambda x: f"{x + 1} / {total_pages} page",
            key="page_selector",
            label_visibility='collapsed'
        )
        if selected_page != current_page:
            return selected_page
    
    with col_next:
        if st.button("Next ▶", disabled=current_page >= total_pages - 1):
            return min(total_pages - 1, current_page + 1)
    
    return None


def render_event_header(event_idx: int, is_checked: bool) -> Tuple[bool, bool]:
    """
    Render event header with checkbox and title. Returns new checked state.
    
    Creates the header section for each event including:
    - Checkbox for marking events as reviewed
    - Event title and number display
    - Delete button for event removal
    
    The header provides visual feedback for the event's review status
    and quick access to deletion functionality.
    
    Args:
        event_idx (int): Index of the event
        is_checked (bool): Current checked status of the event
        
    Returns:
        Tuple[bool, bool]: (new_checked_state, delete_requested)
        
    Example:
        new_checked, delete_requested = render_event_header(0, False)
        if delete_requested:
            # Handle event deletion
    """
    checkbox_col, title_col, btn_col, empty_col = st.columns([0.15, 0.15, 0.1, 0.6])
    
    with checkbox_col:
        new_checked = st.checkbox(
            "_Mark as reviewed_", 
            value=is_checked, 
            key=f"check_event_{event_idx}", 
            help="Check to mark as reviewed",
        )
    
    with title_col:
        if new_checked:
            st.markdown(f"  ### ✓ Event number {event_idx + 1} - CHECKED")
        else:
            st.markdown(f"### Event number {event_idx + 1}")
    
    with btn_col:
        delete_requested = st.button(
            "Delete Event", 
            key=f"delete_event_btn_{event_idx}", 
            type='primary'
        )
    
    return new_checked, delete_requested


def render_event_form(event: Dict, event_idx: int) -> Optional[Dict[str, Any]]:
    """
    Render the event editing form and return form data.
    
    Creates a comprehensive form for editing event data with all necessary fields.
    The form includes special handling for different data types and provides
    a user-friendly interface for event management.
    
    The form features:
    - Organized field layout with logical grouping
    - Dynamic field rendering based on data types
    - Special handling for datetime fields
    - Coordinate display and validation
    - Form validation and error handling
    
    Args:
        event (Dict): Event data dictionary
        event_idx (int): Index of the event being edited
        
    Returns:
        Optional[Dict[str, Any]]: Form data if submitted, None otherwise
        
    Example:
        form_data = render_event_form(event_data, 0)
        if form_data:
            # Process form submission
    """
    event_without_images = {k: v for k, v in event.items() if k != "images"}
    
    with st.form(key=f"event_form_{event_idx}"):
        form_data = {}
        
        # Track original full_address for coordinate updates
        original_full_address = event_without_images.get('full_address', '')
        
        # First row: title, organiser, blurb
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            form_data['title'] = st.text_input(
                'title',
                value=event_without_images.get('title', ''),
                key=f'form_title_{event_idx}'
            )
        with col2:
            form_data['organiser'] = st.text_input(
                'organiser',
                value=event_without_images.get('organiser', ''),
                key=f'form_organiser_{event_idx}'
            )
        with col3:
            form_data['blurb'] = st.text_input(
                'blurb',
                value=event_without_images.get('blurb', ''),
                key=f'form_blurb_{event_idx}'
            )
        
        st.markdown("---")
        
        # Second row: description
        col1, col2 = st.columns([1, 17])
        with col1:
            st.markdown("description")
        with col2:
            form_data['description'] = st.text_area(
                'description',
                value=str(event_without_images.get('description', '')),
                height=120,
                key=f'form_description_{event_idx}',
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        
        # Third row: url with clickable link
        col1, col2 = st.columns([1, 17])
        with col1:
            url_value = str(event_without_images.get('url', ''))
            if url_value.strip():
                st.markdown(
                    f'<a href="{url_value}" target="_blank" style="font-size: 1em; color: #1a73e8; text-decoration: underline; font-weight: bold;">url🔗</a>',
                    unsafe_allow_html=True
                )
        with col2:
            form_data['url'] = st.text_input(
                "url",
                value=url_value,
                key=f'form_url_{event_idx}',
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        
        # Fourth row: activity_or_event & categories
        col1, col2 = st.columns([1, 8])
        with col1:
            current_value = event_without_images.get('activity_or_event', '')
            form_data['activity_or_event'] = st.radio(
                'activity_or_event',
                options=ACTIVITY_OR_EVENT,
                index=ACTIVITY_OR_EVENT.index(current_value) if current_value in ACTIVITY_OR_EVENT else 0,
                help="Event: time-specific or one-off. Activity: available year-round",
                key=f"form_activity_or_event_{event_idx}",
                horizontal=True
            )
        with col2:
            current_categories = event_without_images.get('categories', [])
            form_data['categories'] = st.multiselect(
                'categories',
                options=AVAILABLE_CATEGORIES,
                default=current_categories,
                help="Select one or more categories for this event",
                key=f"form_categories_{event_idx}"
            )
        
        st.markdown("---")
        
        # Fifth row: price_display_teaser price_display, price, is_free
        col1, col2, col3, col4 = st.columns([1, 1, 6, 4])
        with col1:
            form_data['price'] = st.number_input(
                'price',
                value=event_without_images.get('price', 0.0),
                key=f'form_price_{event_idx}'
            )
        with col2:
            form_data['is_free'] = st.radio(
                'is_free',
                options=[True, False],
                index=0 if event_without_images.get('is_free', False) else 1,
                key=f'form_is_free_{event_idx}',
                format_func=lambda x: 'Yes' if x else 'No',
                horizontal=True
            )
        with col3:
            form_data['price_display'] = st.text_input(
                'price_display',
                value=event_without_images.get('price_display', ''),
                key=f'form_price_display_{event_idx}'
            )
        with col4:
            form_data['price_display_teaser'] = st.text_input(
                'price_display_teaser',
                value=event_without_images.get('price_display_teaser', ''),
                key=f'form_price_display_teaser_{event_idx}'
            )
        
        st.markdown("---")
        
        # Sixth row: age_group_display, min_age, max_age
        col1, col2, col3 = st.columns([1, 1, 10])
        with col1:
            form_data['min_age'] = st.number_input(
                'min_age',
                value=float(event_without_images.get('min_age', 0.0)),
                key=f"form_min_age_{event_idx}"
            )
        with col2:
            form_data['max_age'] = st.number_input(
                'max_age',
                value=float(event_without_images.get('max_age', 0.0)),
                key=f"form_max_age_{event_idx}"
            )
        with col3:
            form_data['age_group_display'] = st.text_input(
                'age_group_display',
                value=event_without_images.get('age_group_display', ''),
                key=f'form_age_group_display_{event_idx}'
            )
        
        st.markdown("---")
        
        # Seventh row: datetime_display_teaser, datetime_display, start_datetime, end_datetime
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
        with col1:
            # Parse existing ISO 8601 datetime
            parsed_date, parsed_time = parse_iso_datetime(event_without_images.get('start_datetime', ''))
            
            col1_, col2_ = st.columns([5, 4])
            with col1_:
                start_selected_date = st.date_input(
                    "start_datetime",
                    value=parsed_date if parsed_date else date.today(),
                    key=f"form_start_datetime_date_{event_idx}"
                )
            with col2_:
                start_selected_time = st.time_input(
                    "start_time",
                    value=parsed_time if parsed_time else time(9, 0),
                    key=f"form_start_datetime_time_{event_idx}",
                    label_visibility='hidden'
                )
        
        with col2:
            # Parse existing ISO 8601 datetime
            parsed_end_date, parsed_end_time = parse_iso_datetime(event_without_images.get('end_datetime', ''))
            
            col1_, col2_ = st.columns([5, 4])
            with col1_:
                end_selected_date = st.date_input(
                    "end_datetime",
                    value=parsed_end_date if parsed_end_date else date.today(),
                    key=f"form_end_datetime_date_{event_idx}"
                )

            with col2_:
                end_selected_time = st.time_input(
                    "end_time",
                    value=parsed_end_time if parsed_end_time else time(9, 0),
                    key=f"form_end_datetime_time_{event_idx}",
                    label_visibility='hidden'
                )
        
        with col3:
            form_data['datetime_display'] = st.text_input(
                'datetime_display',
                value=event_without_images.get('datetime_display', ''),
                key=f'form_datetime_display_{event_idx}'
            )

        with col4:
            form_data['datetime_display_teaser'] = st.text_input(
                'datetime_display_teaser',
                value=event_without_images.get('datetime_display_teaser',''),
                key=f'form_datetime_display_teaser_{event_idx}'
                
            )
        
        st.markdown("---")
        
        # Eighth row: venue_name, full_address, latitude, longitude
        latitude = event_without_images.get('latitude', 0.0)
        longitude = event_without_images.get('longitude', 0.0)
        
        # Display "NULL" for latitude/longitude if they are 0 or null
        latitude_display = "NULL" if (latitude == 0.0 or latitude == 0 or latitude is None) else f"{latitude:.6f}"
        longitude_display = "NULL" if (longitude == 0.0 or longitude == 0 or longitude is None) else f"{longitude:.6f}"
        
        col1, col2, col3 = st.columns([1, 1, 7])
        with col1:
            st.metric("Latitude", latitude_display)
        with col2:
            st.metric("Longitude", longitude_display)
        with col3:
            col3a, col3b = st.columns([1, 1])
            with col3a:
                form_data['venue_name'] = st.text_input(
                    'venue_name',
                    value=event_without_images.get('venue_name', ''),
                    key=f"form_venue_name_{event_idx}"
                )
            with col3b:
                form_data['full_address'] = st.text_input(
                    'full_address',
                    value=event_without_images.get('full_address', ''),
                    help="Changing this address will automatically update longitude and latitude.",
                    key=f"form_full_address_{event_idx}"
                )
        
        # Handle dynamic fields
        event_form_display = {k: v for k, v in event_without_images.items() if k not in SPECIAL_FIELDS}
        
        for key, value in event_form_display.items():
            st.markdown("---")
            if isinstance(value, bool):
                form_data[key] = st.radio(
                    key,
                    options=[True, False],
                    index=0 if value else 1,
                    key=f"form_{key}_{event_idx}",
                    format_func=lambda x: 'Yes' if x else 'No',
                    horizontal=True,
                    disabled=key in DISABLED_FIELDS
                )
            elif isinstance(value, (int, float)):
                form_data[key] = st.number_input(
                    key,
                    value=float(value) if value is not None else 0.0,
                    key=f"form_{key}_{event_idx}",
                    disabled=key in DISABLED_FIELDS
                )
            elif isinstance(value, list):
                list_str = json.dumps(value, indent=2, ensure_ascii=False) if value else "[]"
                form_data[key] = st.text_area(
                    key,
                    value=list_str,
                    height=80,
                    help="Edit as JSON array format",
                    key=f"form_{key}_{event_idx}",
                    disabled=key in DISABLED_FIELDS
                )
            elif isinstance(value, dict):
                dict_str = json.dumps(value, indent=2, ensure_ascii=False) if value else "{}"
                form_data[key] = st.text_area(
                    key,
                    value=dict_str,
                    height=120,
                    help="Edit as JSON object format",
                    key=f"form_{key}_{event_idx}",
                    disabled=key in DISABLED_FIELDS
                )
            else:
                form_data[key] = st.text_input(
                    key,
                    value=str(value) if value is not None else "",
                    key=f"form_{key}_{event_idx}",
                    disabled=key in DISABLED_FIELDS
                )
        
        # Handle datetime fields specially
        start_date = st.session_state.get(f"form_start_datetime_date_{event_idx}")
        start_time = st.session_state.get(f"form_start_datetime_time_{event_idx}")
        end_date = st.session_state.get(f"form_end_datetime_date_{event_idx}")
        end_time = st.session_state.get(f"form_end_datetime_time_{event_idx}")
        
        if start_date and start_time:
            form_data['start_datetime'] = combine_to_iso_datetime(start_date, start_time)
        if end_date and end_time:
            form_data['end_datetime'] = combine_to_iso_datetime(end_date, end_time)
        
        # Form submit button
        form_submitted = st.form_submit_button("💾 Save Event Data", type="primary")
        
        if form_submitted:
            form_data['original_full_address'] = original_full_address
            return form_data
    
    return None


def render_image_upload_section(event_idx: int, current_image_count: int, key_suffix: str = "") -> Optional[Any]:
    """
    Render image upload section.
    
    Creates an image upload widget with validation and user feedback.
    Prevents uploads when the maximum image count is reached.
    
    Args:
        event_idx (int): Index of the event
        current_image_count (int): Current number of images for the event
        key_suffix (str): Optional suffix for widget keys
        
    Returns:
        Optional[Any]: Uploaded file object or None
        
    Example:
        uploaded_file = render_image_upload_section(0, 3)
        if uploaded_file:
            # Process uploaded file
    """
    if current_image_count >= MAX_IMAGES_PER_EVENT:
        st.warning(f"Maximum of {MAX_IMAGES_PER_EVENT} images allowed per event.")
        return None
    
    remaining_slots = MAX_IMAGES_PER_EVENT - current_image_count
    return st.file_uploader(
        f"Upload image for Event {event_idx + 1} ({remaining_slots} remaining)",
        type=SUPPORTED_IMAGE_TYPES,
        accept_multiple_files=False,
        key=f"images_upload_{event_idx}{key_suffix}",
        help="Select one image to upload immediately"
    )


def render_success_message(event_idx: int) -> None:
    """
    Render success message if it exists in session state.
    
    Displays success messages stored in session state for specific events.
    Automatically clears the message after display to prevent repetition.
    
    Args:
        event_idx (int): Index of the event for the message
    """
    success_key = f'success_message_{event_idx}'
    
    if success_key in st.session_state:
        success_message = st.session_state[success_key]
        st.success(success_message)
        del st.session_state[success_key]


def render_page_header(pagination_info: Dict[str, int]) -> None:
    """
    Render the page header with pagination information.
    
    Displays comprehensive pagination information including current page,
    total pages, and total events count. Provides pagination controls
    for navigation between pages.
    
    Args:
        pagination_info (Dict[str, int]): Pagination information
        num_total_events (int): Total number of events
    """
    total_pages = pagination_info["total_pages"]
    current_page = pagination_info["current_page"]
    total_events = pagination_info["total_items"]
    
    st.markdown(f"# Total events: {total_events}")
    
    # Pagination controls
    selected_page = render_pagination_controls(pagination_info)
    if selected_page is not None and selected_page != current_page:
        st.session_state['current_page'] = selected_page
        st.rerun()


def render_search_section(events: List[Dict], search_term: str = "", case_sensitive: bool = False) -> Tuple[str, bool, List[Dict]]:
    """
    Render the search section with input field.
    
    Creates a search interface for filtering events by title. Provides
    real-time filtering and user feedback on search results.
    
    The search functionality includes:
    - Text input for search terms
    - Real-time filtering of events
    - Search result statistics
    - User feedback for no results
    
    Args:
        events (List[Dict]): List of all events
        search_term (str): Current search term
        case_sensitive (bool): Whether search is case sensitive (always False now)
        
    Returns:
        Tuple[str, bool, List[Dict]]: (new_search_term, new_case_sensitive, filtered_events)
        
    Example:
        search_term, case_sensitive, filtered_events = render_search_section(events, "art")
    """
    
    # Search input
    new_search_term = st.text_input(
        "Search by event title:",
        value=search_term,
        placeholder="Enter event title to search...",
        help="Search for events by their title. Leave empty to show all events."
    )
    
    # Always use case-insensitive search
    new_case_sensitive = False
    
    # Filter events based on search
    if new_search_term.strip():
        filtered_events = filter_events_by_search(events, new_search_term, new_case_sensitive)
        
        # Show search results summary
        st.info(f"🔍 Found {len(filtered_events)} event(s) matching '{new_search_term}'")
        
        if len(filtered_events) == 0:
            st.warning("No events found matching your search criteria.")
    else:
        filtered_events = events
    
    return new_search_term, new_case_sensitive, filtered_events


import json  # Import needed for the dynamic fields handling 