import streamlit as st
import json
import re
from pathlib import Path
from datetime import datetime, date, time

st.set_page_config(page_title="Event JSON & Image Editor", layout="wide")

# Import Google Places functionality
try:
    from src.services.places import get_coordinates_from_address
    GOOGLE_PLACES_AVAILABLE = True
except (ImportError, ValueError, FileNotFoundError) as e:
    GOOGLE_PLACES_AVAILABLE = False
    st.warning(f"Google Places API not available. Longitude/Latitude will not be auto-updated. Error: {e}")
    
    # Create a dummy function to prevent errors
    def get_coordinates_from_address(address):
        return None, None

# Load event schema to get available categories
with open("config/event_schema.json", 'r', encoding='utf-8') as f:
    event_schema = json.load(f)

# Extract categories from schema
AVAILABLE_CATEGORIES = event_schema["items"]["properties"]["categories"]["items"]["enum"]
ACTIVITY_OR_EVENT = event_schema["items"]["properties"]["activity_or_event"]['enum']
# Helper functions for ISO 8601 datetime conversion
def parse_iso_datetime(iso_string):
    """Parse ISO 8601 datetime string into date and time objects.
    
    Args:
        iso_string (str): ISO 8601 formatted datetime string
        
    Returns:
        tuple: (date_obj, time_obj) or (None, None) if parsing fails
    """
    if not iso_string or not isinstance(iso_string, str):
        return None, None
    
    try:
        # Handle various ISO 8601 formats
        iso_string = iso_string.strip()
        
        # Remove timezone info for parsing (Z or +XX:XX format)
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1]
        elif '+' in iso_string[-6:] or iso_string.count('-') > 2:
            # Remove timezone offset like +08:00 or +0800
            if '+' in iso_string:
                iso_string = iso_string.split('+')[0]
            elif iso_string.count('-') > 2:  # More than 2 dashes means timezone
                parts = iso_string.split('-')
                iso_string = '-'.join(parts[:3]) + 'T' + parts[3].split('T')[1] if 'T' in iso_string else '-'.join(parts[:3])
        
        # Parse the datetime
        if 'T' in iso_string:
            dt = datetime.fromisoformat(iso_string)
        else:
            # If no time component, assume it's just a date
            dt = datetime.strptime(iso_string, '%Y-%m-%d')
        
        return dt.date(), dt.time()
    
    except (ValueError, AttributeError, IndexError):
        # If parsing fails, try to extract just the date
        try:
            date_part = iso_string.split('T')[0] if 'T' in iso_string else iso_string
            dt = datetime.strptime(date_part, '%Y-%m-%d')
            return dt.date(), None
        except:
            return None, None

def combine_to_iso_datetime(date_obj, time_obj):
    """Combine date and time objects into ISO 8601 string.
    
    Args:
        date_obj (date): Date object
        time_obj (time): Time object
        
    Returns:
        str: ISO 8601 formatted datetime string or None
    """
    if not date_obj:
        return None
    
    if time_obj:
        dt = datetime.combine(date_obj, time_obj)
        return dt.isoformat()
    else:
        # If no time, use midnight
        dt = datetime.combine(date_obj, time.min)
        return dt.isoformat()



st.title("Event JSON & Image Editor")

# Add aspect ratio controls
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 🖼️ Image Display Settings")

with col2:
    # Aspect ratio selector
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["Original", "4:3", "16:9"],
        index=0,
        help="Select how images should be displayed"
    )

# Store aspect ratio in session state
st.session_state['aspect_ratio'] = aspect_ratio

st.divider()

# Helper function to calculate image display parameters
def get_image_display_params(aspect_ratio, base_width=1000):
    """Calculate image display parameters based on selected aspect ratio.
    
    Args:
        aspect_ratio (str): Selected aspect ratio ("Original", "4:3", "16:9")
        base_width (int): Base width for image display
        
    Returns:
        dict: Dictionary with CSS style and streamlit parameters
    """
    if aspect_ratio == "4:3":
        # 4:3 aspect ratio
        height = int(base_width * 3 / 4)
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": f"width: {base_width}px; height: {height}px; object-fit: cover;"
        }
    elif aspect_ratio == "16:9":
        # 16:9 aspect ratio  
        height = int(base_width * 9 / 16)
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": f"width: {base_width}px; height: {height}px; object-fit: cover;"
        }
    else:  # Original
        return {
            "width": base_width,
            "use_container_width": False,
            "css_style": None
        }

def display_image_with_aspect_ratio(image_path, aspect_ratio="Original", base_width=1000):
    """Display an image with the specified aspect ratio."""
    params = get_image_display_params(aspect_ratio, base_width)
    
    if params["css_style"]:
        # Use HTML/CSS for aspect ratio control
        import base64
        try:
            # Read and encode image
            with open(image_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
            # Determine image format
            img_format = Path(image_path).suffix.lower()
            if img_format == '.jpg' or img_format == '.jpeg':
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
                <img src=\"data:{mime_type};base64,{img_data}\" 
                     style=\"{params['css_style']}\" 
                     alt=\"\">
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)
        except Exception as e:
            # Fallback to regular st.image if HTML approach fails
            st.image(image_path, width=params["width"], use_container_width=params["use_container_width"])
    else:
        # Use regular st.image for original aspect ratio (no caption)
        st.image(image_path, width=params["width"], use_container_width=params["use_container_width"])



def find_event_json_files(base_dir):
    base = Path(base_dir)
    event_files = []
    for folder in base.glob("*/"):
        for json_file in folder.glob("*.json"):
            event_files.append(json_file)
    return event_files

def get_event_images(event_folder, blog_source):
    images_dir = event_folder / "images" / blog_source
    if images_dir.exists():
        return list(images_dir.glob("*"))
    return []

if 'deleted_image_slot' not in st.session_state:
    st.session_state['deleted_image_slot'] = None



if 'delete_event_idx' not in st.session_state:
    st.session_state['delete_event_idx'] = None

# Pagination settings
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 0

if 'events_per_page' not in st.session_state:
    st.session_state['events_per_page'] = 10

# Popup confirmation for event deletion
@st.dialog("Delete Event Confirmation")
def confirm_delete_event(event_idx, event, events, selected_file):
    st.write("Are you sure you want to delete this event and all its images?")
    st.write(f"**Event:** {event.get('title', 'Untitled Event')}")
    st.write(f"**Images to delete:** {len(event.get('images', []))}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            # Delete all associated image files
            for img_obj in event.get('images', []):
                local_path = img_obj.get('local_path')
                if local_path:
                    img_file = Path(local_path)
                    if img_file.exists():
                        img_file.unlink()
            # Delete the event
            events.pop(event_idx)
            Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
            
            # Update pagination after deletion
            new_total = len(events)
            events_per_page = st.session_state['events_per_page']
            new_total_pages = (new_total + events_per_page - 1) // events_per_page if new_total > 0 else 0
            
            # If current page is now beyond the last page, go to the last page
            if st.session_state['current_page'] >= new_total_pages and new_total_pages > 0:
                st.session_state['current_page'] = new_total_pages - 1
            elif new_total == 0:
                st.session_state['current_page'] = 0
            
            st.success("Event and all images deleted!")
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# Popup confirmation for image deletion
@st.dialog("Delete Image Confirmation")
def confirm_delete_image(event_idx, img_idx, img_obj, event, events, selected_file):
    st.write("Are you sure you want to delete this image?")
    
    # Show image preview if available
    local_path = "data\\" + img_obj.get("local_path", "")
    if local_path:
        img_file = Path(local_path)
        if img_file.exists():
            # Use aspect ratio setting for delete confirmation preview (smaller size)
            current_aspect_ratio = st.session_state.get('aspect_ratio', 'Original')
            display_image_with_aspect_ratio(str(img_file), current_aspect_ratio, 300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            if local_path:
                img_file = Path(local_path)
                if img_file.exists():
                    img_file.unlink()
            event["images"].pop(img_idx)
            events[event_idx] = event
            Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
            st.success("Image deleted!")
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# 1. Select event JSON file
event_json_files = find_event_json_files("data/events_output")
if not event_json_files:
    st.warning("No event JSON files found in data/events_output.")
    st.stop()

selected_file = st.selectbox(
    "Select an event JSON file to edit:",
    event_json_files,
    format_func=lambda p: str(p.relative_to(Path("data/events_output")))
)

# 2. Load JSON (expecting a list of events)
try:
    events = json.loads(Path(selected_file).read_text(encoding="utf-8"))
    if not isinstance(events, list):
        st.error("JSON file does not contain a list of events.")
        st.stop()
except Exception as e:
    st.error(f"Failed to load JSON: {e}")
    st.stop()

# 3. Calculate pagination
total_events = len(events)
events_per_page = st.session_state['events_per_page']
total_pages = (total_events + events_per_page - 1) // events_per_page  # Ceiling division
current_page = st.session_state['current_page']

# Ensure current page is valid
if current_page >= total_pages and total_pages > 0:
    st.session_state['current_page'] = total_pages - 1
    current_page = st.session_state['current_page']

# Calculate start and end indices for current page
start_idx = current_page * events_per_page
end_idx = min(start_idx + events_per_page, total_events)
current_page_events = events[start_idx:end_idx]

# Display header with pagination info
col1, col2 = st.columns([3, 1])
with col1:
    if total_pages > 0:
        st.header(f"Showing events {start_idx + 1}–{end_idx} of {total_events}")
    else:
        st.header("No events found")
with col2:
    if total_pages > 1:
        # Pagination controls
        col_prev, col_page, col_next = st.columns([1, 3, 1])
        with col_prev:
            if st.button("◀ Prev", disabled=current_page == 0):
                st.session_state['current_page'] = max(0, current_page - 1)
                st.rerun()
        with col_page:
            # Page selector dropdown for quick navigation
            selected_page = st.selectbox(
                "Page",
                options=range(total_pages),
                index=current_page,
                format_func=lambda x: f"{x + 1} / {total_pages} page",
                key="page_selector",
                label_visibility='collapsed'
            )
            if selected_page != current_page:
                st.session_state['current_page'] = selected_page
                st.rerun()
        with col_next:
            if st.button("Next ▶", disabled=current_page >= total_pages - 1):
                st.session_state['current_page'] = min(total_pages - 1, current_page + 1)
                st.rerun()


for page_event_idx, event in enumerate(current_page_events):
    # Calculate actual event index in the full list
    event_idx = start_idx + page_event_idx
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
    event_without_images = {k: v for k, v in event.items() if k != "images"}
    title_col, btn_col = st.columns([0.9, 0.1])
    with title_col:
        st.markdown(f"## Event number {event_idx + 1}")
    with btn_col:
        if st.button("Delete", key=f"delete_event_btn_{event_idx}"):
            confirm_delete_event(event_idx, event, events, selected_file)

    # Create an interactive form for editing event data
    
    with st.form(key=f"event_form_{event_idx}"):
        # Create a dictionary to store the form values
        form_data = {}
        
        # Track original full_address for coordinate updates
        original_full_address = event_without_images.get('full_address', '')
        
        special_fields = ['title', 'organiser', 'blurb',
                          'description',
                          'url',
                          'activity_or_event', 'categories',
                          'price_display', 'price', 'is_free', 
                          'age_group_display', 'min_age', 'max_age', 
                          'datetime_display', 'start_datetime', 'end_datetime', 
                          'venue_name','full_address', 'latitude', 'longitude']
        field_to_disabled = ['guid', 'scraped_on' ,'latitude', 'longitude']
        event_form_display = {k:v for k,v in event_without_images.items() if k not in special_fields}


        # First row : title and blurb
        col1, col2, col3 = st.columns([1,1,3])
        with col1:
            form_data['title'] = st.text_input(
                'title',
                value=event_without_images.get('title', ''),
                key=f'form_title_{event_idx}'
            )
        with col2:
            form_data['organiser']=st.text_input(
                'organiser',
                value = event_without_images.get('organiser', ''),
                key=f'form_organiser_{event_idx}'
            )
        with col3:
            form_data['blurb'] = st.text_input(
                'blurb',
                value=event_without_images.get('blurb', ''),
                key=f'form_blurb_{event_idx}'
            )

        
        st.markdown("---")
        #Second row : description
        col1,col2=st.columns([1,17])
        with col1:
            st.markdown("description")
        with col2:
            form_data['description'] = st.text_area(
                'description',
                value = str(event_without_images.get('description', '')),
                height=120,
                key=f'form_description_{event_idx}',
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        # Third row : url with clickable link
        col1,col2 = st.columns([1, 17])
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
        # Forth row : activity_or_event & categories
        col1, col2 = st.columns([1,8])
        with col1:
                options = ACTIVITY_OR_EVENT
                current_value = event_without_images.get('activity_or_event', '') 
                
                form_data['activity_or_event'] = st.radio(
                    'activity_or_event',
                    options=ACTIVITY_OR_EVENT,
                    index=ACTIVITY_OR_EVENT.index(current_value),
                    help="Event: time-specific or one-off. Activity: available year-round",
                    key=f"form_activity_or_event_{event_idx}",
                    horizontal=True
                )
        with col2:
            current_categories = event_without_images.get('categories', '') 
            form_data['categories'] = st.multiselect(
                'categories',
                options=AVAILABLE_CATEGORIES,
                default=current_categories,
                help="Select one or more categories for this event",
                key=f"form_categories_{event_idx}"
            )

        
        st.markdown("---")
        # Fifth row : price_display, price, is_free
        col1,col2,col3 = st.columns([1,1,10])
        with col1:
            form_data['price'] = st.number_input(
                'price',
                value = event_without_images.get('price', ''),
                key=f'form_price_{event_idx}'
            )
        with col2:
            form_data['is_free'] = st.radio(
                'is_free',
                options=[True, False],
                index=0 if event_without_images.get('is_free', '') else 1,
                key=f'form_is_free_{event_idx}',
                format_func=lambda x: 'Yes' if x else 'No',
                horizontal=True
            )
        with col3:
            form_data['price_display'] = st.text_input(
                'price_display',
                value = event_without_images.get('price_display', ''),
                key=f'form_price_display_{event_idx}'
            )
        st.markdown("---")
        # sixth row : age_group_display, min_age, max_age
        col1,col2,col3= st.columns([1,1,10])
        with col1:
            form_data['min_age'] = st.number_input(
                'min_age',
                value=float(event_without_images.get('min_age', '')),
                key=f"form_min_age_{event_idx}"
            )
        with col2:
            form_data['max_age'] = st.number_input(
                'max_age',
                value=float(event_without_images.get('max_age', '')),
                key=f"form_max_age_{event_idx}"
            )
        with col3:
            form_data['age_group_display'] = st.text_input(
                'age_group_display',
                value=event_without_images.get('age_group_display', ''),
                key=f'form_age_group_display_{event_idx}'
            )

        st.markdown("---")
        #seventh row : datetime_display, start_datetime, end_datetime 
        col1, col2, col3 = st.columns([1,1,5])
        with col1:
            # Parse existing ISO 8601 datetime
            parsed_date, parsed_time = parse_iso_datetime(event_without_images.get('start_datetime', ''))
            
            col1_, col2_ = st.columns([5,4])
            with col1_:
                start_selected_date = st.date_input(
                    "start_datetime",
                    value=parsed_date if parsed_date else date.today(),
                    key=f"form_start_datetime_date_{event_idx}"
                )
            
            with col2_:
                start_selected_time = st.time_input(
                    "start_time",
                    value=parsed_time if parsed_time else time(9, 0),  # Default to 9:00 AM
                    key=f"form_start_datetime_time_{event_idx}",
                    label_visibility='hidden'
                )
            
        with col2:
            # Parse existing ISO 8601 datetime
            parsed_end_date, parsed_end_time = parse_iso_datetime(event_without_images.get('end_datetime', ''))
            
            col1_, col2_ = st.columns([5,4])
            with col1_:
                end_selected_date = st.date_input(
                    "end_datetime",
                    value=parsed_end_date if parsed_end_date else date.today(),
                    key=f"form_end_datetime_date_{event_idx}"
                )
            with col2_:
                end_selected_time = st.time_input(
                    "end_time",
                    value=parsed_end_time if parsed_end_time else time(9, 0),  # Default to 9:00 AM
                    key=f"form_end_datetime_time_{event_idx}",
                    label_visibility='hidden'
                )
        
        with col3:
            form_data['datetime_display'] = st.text_input(
                'datetime_display',
                value = event_without_images.get('datetime_display', ''),
                key=f'form_datetime_display_{event_idx}'
            )
        
        st.markdown("---")
        #eigth row : venue_name,full_address,latitude, longitude
        latitude = event_without_images.get('latitude', 0.0)
        longitude = event_without_images.get('longitude', 0.0)
        col1,col2,col3 = st.columns([1,1,7])
        with col1:
            st.metric("Latitude", f"{latitude:.6f}")
        with col2:
            st.metric("Longitude", f"{longitude:.6f}")
        with col3:
            col3a, col3b = st.columns([1, 1])
            with col3a:
                form_data['venue_name'] = st.text_input(
                    'venue_name',
                    value= event_without_images.get('venue_name', ''),
                    key=f"form_venue_name_{event_idx}"
                )
            with col3b:
                form_data['full_address'] = st.text_input(
                    'full_address',
                    value= event_without_images.get('full_address', ''),
                    help="Changing this address will automatically update longitude and latitude",
                    key=f"form_full_address_{event_idx}"
                )


        for key, value in event_form_display.items():
            st.markdown("---")
            if isinstance(value, bool):
                # Radio for boolean values (True/False)
                form_data[key] = st.radio(
                    key,
                    options=[True, False],
                    index=0 if value else 1,
                    key=f"form_{key}_{event_idx}",
                    format_func=lambda x: 'Yes' if x else 'No',
                    horizontal=True,
                    disabled = key in field_to_disabled
                )
            elif isinstance(value, (int, float)):
                # Number input for numeric values
                form_data[key] = st.number_input(
                    key,
                    value=float(value) if value is not None else 0.0,
                    key=f"form_{key}_{event_idx}",
                    disabled = key in field_to_disabled
                )
            elif isinstance(value, list):
                # Text area for other lists (convert to/from JSON-like format)
                list_str = json.dumps(value, indent=2, ensure_ascii=False) if value else "[]"
                form_data[key] = st.text_area(
                    key,
                    value=list_str,
                    height=80,
                    help="Edit as JSON array format",
                    key=f"form_{key}_{event_idx}",
                    disabled = key in field_to_disabled
                )
            elif isinstance(value, dict):
                # Text area for dict values (convert to/from JSON format)
                dict_str = json.dumps(value, indent=2, ensure_ascii=False) if value else "{}"
                form_data[key] = st.text_area(
                    key,
                    value=dict_str,
                    height=120,
                    help="Edit as JSON object format",
                    key=f"form_{key}_{event_idx}",
                    disabled = key in field_to_disabled
                )
            else:
                # Default text input for everything else (including datetime_display, etc.)
                form_data[key] = st.text_input(
                    key,
                    value=str(value) if value is not None else "",
                    key=f"form_{key}_{event_idx}",
                    disabled = key in field_to_disabled
                )
        
        # Form submit button
        form_submitted = st.form_submit_button("💾 Save Event Data", type="primary")
        
        if form_submitted:
            try:
                # First, capture ALL form values including datetime combinations
                # Handle datetime fields specially - combine date and time inputs
                start_date = st.session_state.get(f"form_start_datetime_date_{event_idx}")
                start_time = st.session_state.get(f"form_start_datetime_time_{event_idx}")
                end_date = st.session_state.get(f"form_end_datetime_date_{event_idx}")
                end_time = st.session_state.get(f"form_end_datetime_time_{event_idx}")
                
                # Combine datetime fields
                if start_date and start_time:
                    form_data['start_datetime'] = combine_to_iso_datetime(start_date, start_time)
                if end_date and end_time:
                    form_data['end_datetime'] = combine_to_iso_datetime(end_date, end_time)
                
                # Check if full_address has changed and update coordinates
                new_full_address = form_data.get('full_address', '')
                latitude = event_without_images.get('latitude', 0.0)
                longitude = event_without_images.get('longitude', 0.0)
                coordinates_updated = False
                
                if new_full_address != original_full_address and new_full_address.strip():
                    if GOOGLE_PLACES_AVAILABLE:
                        with st.spinner("🌍 Address changed. Looking up new coordinates..."):
                            new_longitude, new_latitude = get_coordinates_from_address(new_full_address)
                            if new_longitude is not None and new_latitude is not None:
                                longitude = new_longitude
                                latitude = new_latitude
                                coordinates_updated = True
                            else:
                                st.warning("⚠️ Could not find coordinates for the new address. Longitude and latitude will remain unchanged.")
                    else:
                        st.warning("⚠️ Google Places API not available. Cannot update coordinates automatically.")
                
                # Process ALL form data and convert to appropriate types
                updated_event_data = {}
                
                # Set coordinates (either updated or original)
                updated_event_data['latitude'] = latitude
                updated_event_data['longitude'] = longitude
                
                # Process all other form fields
                for key, form_value in form_data.items():
                    original_value = event_without_images.get(key)
                    
                    if key in ['latitude', 'longitude']:
                        # Already handled above
                        continue
                    elif isinstance(original_value, bool):
                        updated_event_data[key] = form_value
                    elif isinstance(original_value, (int, float)):
                        updated_event_data[key] = form_value
                    elif key == 'categories':
                        updated_event_data[key] = form_value
                    elif key in ['start_datetime', 'end_datetime']:
                        updated_event_data[key] = form_value
                    elif isinstance(original_value, list):
                        try:
                            updated_event_data[key] = json.loads(form_value) if form_value.strip() else []
                        except json.JSONDecodeError:
                            st.error(f"Invalid JSON format for field '{key}'. Please check the syntax.")
                            st.stop()
                    elif isinstance(original_value, dict):
                        try:
                            updated_event_data[key] = json.loads(form_value) if form_value.strip() else {}
                        except json.JSONDecodeError:
                            st.error(f"Invalid JSON format for field '{key}'. Please check the syntax.")
                            st.stop()
                    else:
                        updated_event_data[key] = form_value if form_value != "" else None

                # Capture any additional fields from the dynamic form fields (event_form_display)
                for key in event_form_display.keys():
                    if key not in updated_event_data:
                        # Get the form value from session state
                        session_key = f"form_{key}_{event_idx}"
                        if session_key in st.session_state:
                            form_value = st.session_state[session_key]
                            original_value = event_without_images.get(key)
                            
                            if isinstance(original_value, bool):
                                updated_event_data[key] = form_value
                            elif isinstance(original_value, (int, float)):
                                updated_event_data[key] = form_value
                            elif isinstance(original_value, list):
                                try:
                                    updated_event_data[key] = json.loads(form_value) if form_value.strip() else []
                                except json.JSONDecodeError:
                                    updated_event_data[key] = []
                            elif isinstance(original_value, dict):
                                try:
                                    updated_event_data[key] = json.loads(form_value) if form_value.strip() else {}
                                except json.JSONDecodeError:
                                    updated_event_data[key] = {}
                            else:
                                updated_event_data[key] = form_value if form_value != "" else None
                # Add back the images data
                updated_event_data["images"] = event.get("images", [])

                # Ensure all expected fields are present in the event data
                for field in special_fields:
                    if field not in updated_event_data:
                        # Set default values based on type
                        if field in ['price', 'min_age', 'max_age', 'latitude', 'longitude']:
                            updated_event_data[field] = 0.0
                        elif field in ['is_free']:
                            updated_event_data[field] = False
                        elif field in ['categories']:
                            updated_event_data[field] = []
                        elif field in ['description', 'title', 'blurb', 'organiser', 'url', 'price_display', 'age_group_display', 'datetime_display', 'start_datetime', 'end_datetime', 'venue_name', 'full_address']:
                            updated_event_data[field] = ''
                        else:
                            updated_event_data[field] = None

                # Save the updated event data
                events[event_idx] = updated_event_data
                Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                
                # Build detailed success message showing what changed
                changes_made = []
                
                # Check each field for changes
                for key, new_value in updated_event_data.items():
                    if key == "images":  # Skip images
                        continue
                        
                    original_value = event_without_images.get(key)
                    
                    # Compare values (handle different types)
                    if str(new_value) != str(original_value):
                        if key == 'latitude' and coordinates_updated:
                            continue  # Will be handled in coordinates section
                        elif key == 'longitude' and coordinates_updated:
                            continue  # Will be handled in coordinates section
                        else:
                            # Format the change nicely
                            field_name = key.replace('_', ' ').title()
                            if isinstance(new_value, list):
                                if len(str(new_value)) > 50:
                                    changes_made.append(f"📝 {field_name}: Updated")
                                else:
                                    changes_made.append(f"📝 {field_name}: {new_value}")
                            elif isinstance(new_value, bool):
                                changes_made.append(f"📝 {field_name}: {'Yes' if new_value else 'No'}")
                            elif key in ['price', 'min_age', 'max_age']:
                                changes_made.append(f"📝 {field_name}: {new_value}")
                            elif len(str(new_value)) > 50:
                                changes_made.append(f"📝 {field_name}: Updated")
                            else:
                                changes_made.append(f"📝 {field_name}: {new_value}")
                
                # Add coordinates update if address changed
                if coordinates_updated:
                    changes_made.append(f"🌍 Coordinates: {latitude:.6f}, {longitude:.6f}")
                
                # Build the success message
                if changes_made:
                    success_message = f"✅ Event {event_idx + 1} updated successfully!\n" + "\n".join(changes_made)
                else:
                    success_message = f"✅ Event {event_idx + 1} data refreshed (no changes detected)"
                
                st.session_state[f'success_message_{event_idx}'] = success_message
                
                # Force immediate UI update by rerunning the app
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error saving event data: {str(e)}")
    
    # Check for and display any success message from previous save (right after the form)
    success_key = f'success_message_{event_idx}'
    
    if success_key in st.session_state:
        success_message = st.session_state[success_key]
        
        # Display the message
        st.success(success_message)
        
        # Clear after showing
        del st.session_state[success_key]
    
    # Image management for this event
    images = event.get("images", [])
    if not images:
        st.info(f"No images found for Event {event_idx + 1}.")
        
        # Add new images section when no images exist
        st.markdown("### 📁 Add New Images")
        uploaded_files = st.file_uploader(
            f"Upload images for Event {event_idx + 1}",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"new_images_upload_{event_idx}",
            help="You can select multiple images at once"
        )
        
        if uploaded_files:
            st.markdown("#### 🏷️ Customize Image Names")
            
            # Create containers for custom filenames
            custom_filenames = {}
            for file_idx, uploaded_file in enumerate(uploaded_files):
                original_name = Path(uploaded_file.name).stem
                file_extension = Path(uploaded_file.name).suffix
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    custom_filename = st.text_input(
                        f"Name for '{uploaded_file.name}'",
                        value=original_name,
                        help=f"Extension '{file_extension}' will be added automatically",
                        key=f"new_img_name_{event_idx}_{file_idx}"
                    )
                    
                    # Sanitize filename
                    if custom_filename:
                        custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip())
                        if not custom_filename:
                            custom_filename = original_name
                    else:
                        custom_filename = original_name
                    
                    custom_filenames[file_idx] = f"{custom_filename}{file_extension}"
                
                with col2:
                    # Show preview filename
                    st.text_input(
                        "Final filename",
                        value=custom_filenames[file_idx],
                        disabled=True,
                        key=f"preview_name_{event_idx}_{file_idx}"
                    )
            
            # Upload button
            if st.button(f"💾 Upload {len(uploaded_files)} Image(s)", key=f"upload_new_images_{event_idx}", type="primary"):
                try:
                    # Determine save directory - use same structure as existing code
                    save_dir = Path("data/events_output")
                    
                    # Try to use the same directory structure as other events
                    if event_idx < len(events) - 1:  # If there are other events, check their structure
                        for other_event in events:
                            if other_event.get("images") and other_event["images"][0].get("local_path"):
                                # Use similar directory structure
                                example_path = Path(other_event["images"][0]["local_path"])
                                if len(example_path.parts) > 1:
                                    save_dir = Path("data/events_output") / example_path.parts[0]
                                break
                    
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Initialize images array if it doesn't exist
                    if "images" not in event:
                        event["images"] = []
                    
                    # Save each uploaded file
                    uploaded_count = 0
                    for file_idx, uploaded_file in enumerate(uploaded_files):
                        final_filename = custom_filenames[file_idx]
                        save_path = save_dir / final_filename
                        
                        # Handle duplicate filenames by adding a number
                        counter = 1
                        original_save_path = save_path
                        while save_path.exists():
                            name_part = original_save_path.stem
                            ext_part = original_save_path.suffix
                            save_path = original_save_path.parent / f"{name_part}_{counter}{ext_part}"
                            counter += 1
                        
                        # Save the file
                        save_path.write_bytes(uploaded_file.getbuffer())
                        
                        # Add to event's images array
                        new_img_obj = {
                            "local_path": str(save_path).replace("data\\", "").replace("data/", ""),
                            "filename": save_path.name,
                            "original_url": "",  # No URL since it's uploaded
                            "source_credit": "User Upload"
                        }
                        event["images"].append(new_img_obj)
                        uploaded_count += 1
                    
                    # Update the events list and save to file
                    events[event_idx] = event
                    Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                    
                    st.success(f"✅ Successfully uploaded {uploaded_count} image(s) to Event {event_idx + 1}!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error uploading images: {str(e)}")
    else:
        img_idx = 0
        while img_idx < len(images):
            img_obj = images[img_idx]
            st.markdown(f"### Image {img_idx + 1}")
            local_path = "data\\" + img_obj.get("local_path")
            filename = img_obj.get("filename", Path(local_path).name if local_path else "")
            if not local_path:
                img_idx += 1
                continue
            img_file = Path(local_path)

            img_col, meta_col = st.columns([4, 3])
            with img_col:
                if img_file.exists():
                    # Use the selected aspect ratio for main image display
                    current_aspect_ratio = st.session_state.get('aspect_ratio', 'Original')
                    display_image_with_aspect_ratio(str(img_file), current_aspect_ratio, 1000)
                else:
                    st.warning(f"Image not found: {img_file}")
                
                # Delete button below the image with increased height
                st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing above
                
                if st.button(f"🗑️ Delete Image", key=f"delete_btn_{event_idx}_{img_idx}", use_container_width=True, type='primary'):
                    confirm_delete_image(event_idx, img_idx, img_obj, event, events, selected_file)
                st.markdown("<br>", unsafe_allow_html=True)
            
            with meta_col:
                # Always display image metadata in form format
                with st.form(key=f"img_form_{event_idx}_{img_idx}"):
                    st.markdown("**📝 Image Metadata**")
                    
                    # File uploader for replacing image
                    new_img_file = st.file_uploader(
                        f"Replace image file (optional)",
                        type=["jpg","jpeg","png","webp"],
                        key=f"replace_img_upload_{event_idx}_{img_idx}",
                        help="Upload a new image to replace the current one"
                    )
                    
                    # Custom filename input when an image is uploaded
                    custom_filename = ""
                    if new_img_file:
                        # Get the original filename and extension
                        original_name = Path(new_img_file.name).stem
                        file_extension = Path(new_img_file.name).suffix
                        
                        custom_filename = st.text_input(
                            f"Custom filename",
                            value=original_name,
                            help=f"Extension '{file_extension}' will be added automatically.",
                            key=f"custom_filename_{event_idx}_{img_idx}"
                        )
                        
                        # Sanitize filename to remove invalid characters
                        if custom_filename:
                            custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip())
                            if not custom_filename:
                                custom_filename = original_name
                        else:
                            custom_filename = original_name
                    
                    # Create form fields for image metadata
                    img_form_data = {}
                    
                    # Standard image fields
                    img_form_data['filename'] = st.text_input(
                        "Filename",
                        value=img_obj.get('filename', ''),
                        key=f"img_filename_{event_idx}_{img_idx}"
                    )
                    
                    img_form_data['local_path'] = st.text_input(
                        "Local Path",
                        value=img_obj.get('local_path', ''),
                        help="Path to the image file",
                        key=f"img_local_path_{event_idx}_{img_idx}"
                    )
                    
                    img_form_data['original_url'] = st.text_input(
                        "Original URL",
                        value=img_obj.get('original_url', ''),
                        help="URL where the image was originally found",
                        key=f"img_original_url_{event_idx}_{img_idx}"
                    )
                    
                    img_form_data['source_credit'] = st.text_input(
                        "Source Credit",
                        value=img_obj.get('source_credit', ''),
                        help="Credit or attribution for the image source",
                        key=f"img_source_credit_{event_idx}_{img_idx}"
                    )
                    
                    # Handle any additional fields that aren't standard
                    additional_fields = {}
                    for key, value in img_obj.items():
                        if key not in ['filename', 'local_path', 'original_url', 'source_credit']:
                            if isinstance(value, str):
                                additional_fields[key] = st.text_input(
                                    key.replace('_', ' ').title(),
                                    value=value,
                                    key=f"img_{key}_{event_idx}_{img_idx}"
                                )
                            elif isinstance(value, (int, float)):
                                additional_fields[key] = st.number_input(
                                    key.replace('_', ' ').title(),
                                    value=float(value),
                                    key=f"img_{key}_{event_idx}_{img_idx}"
                                )
                            elif isinstance(value, bool):
                                additional_fields[key] = st.checkbox(
                                    key.replace('_', ' ').title(),
                                    value=value,
                                    key=f"img_{key}_{event_idx}_{img_idx}"
                                )
                            else:
                                # For complex types, use text area with JSON
                                additional_fields[key] = st.text_area(
                                    key.replace('_', ' ').title(),
                                    value=json.dumps(value, indent=2, ensure_ascii=False) if value else "",
                                    height=60,
                                    key=f"img_{key}_{event_idx}_{img_idx}"
                                )
                    
                    # Form submit button
                    save_img_metadata = st.form_submit_button("💾 Save Image", type="primary")
                    
                    if save_img_metadata:
                        try:
                            # Build updated image object
                            updated_img_obj = {}
                            
                            # Add standard fields
                            for key, value in img_form_data.items():
                                updated_img_obj[key] = value if value != "" else ""
                            
                            # Add additional fields, converting back to original types
                            for key, form_value in additional_fields.items():
                                original_value = img_obj.get(key)
                                if isinstance(original_value, str):
                                    updated_img_obj[key] = form_value
                                elif isinstance(original_value, (int, float)):
                                    updated_img_obj[key] = form_value
                                elif isinstance(original_value, bool):
                                    updated_img_obj[key] = form_value
                                else:
                                    try:
                                        updated_img_obj[key] = json.loads(form_value) if form_value.strip() else None
                                    except json.JSONDecodeError:
                                        st.error(f"Invalid JSON format for field '{key}'. Please check the syntax.")
                                        st.stop()
                            
                            # If a new image file is uploaded, save it and update metadata
                            if new_img_file:
                                # Save to same folder as previous image
                                if img_obj.get("local_path"):
                                    save_dir = Path("data/events_output") / Path(img_obj["local_path"]).parent
                                else:
                                    save_dir = Path("data/events_output")
                                save_dir.mkdir(parents=True, exist_ok=True)
                                
                                # Use custom filename with original extension
                                file_extension = Path(new_img_file.name).suffix
                                final_filename = f"{custom_filename}{file_extension}"
                                save_path = save_dir / final_filename
                                
                                # Handle duplicate filenames by adding a number
                                counter = 1
                                original_save_path = save_path
                                while save_path.exists():
                                    name_part = original_save_path.stem
                                    ext_part = original_save_path.suffix
                                    save_path = original_save_path.parent / f"{name_part}_{counter}{ext_part}"
                                    counter += 1
                                
                                save_path.write_bytes(new_img_file.getbuffer())
                                updated_img_obj["local_path"] = str(save_path).replace("data\\", "").replace("data/", "")
                                updated_img_obj["filename"] = save_path.name
                            
                            # Update the event
                            event["images"][img_idx] = updated_img_obj
                            events[event_idx] = event
                            Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                            st.success(f"✅ Image {img_idx + 1} metadata saved!")
                            st.rerun()
                            
                        except Exception as e:
                                                         st.error(f"❌ Error saving image metadata: {str(e)}")
            
            st.divider()
            img_idx += 1
        
        # Add section to upload additional images even when images already exist
        st.markdown("### ➕ Add More Images")
        additional_files = st.file_uploader(
            f"Upload additional images for Event {event_idx + 1}",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"additional_images_upload_{event_idx}",
            help="Add more images to this event"
        )
        
        if additional_files:
            st.markdown("#### 🏷️ Customize Additional Image Names")
            
            # Create containers for custom filenames
            additional_custom_filenames = {}
            for file_idx, uploaded_file in enumerate(additional_files):
                original_name = Path(uploaded_file.name).stem
                file_extension = Path(uploaded_file.name).suffix
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    custom_filename = st.text_input(
                        f"Name for '{uploaded_file.name}'",
                        value=original_name,
                        help=f"Extension '{file_extension}' will be added automatically",
                        key=f"additional_img_name_{event_idx}_{file_idx}"
                    )
                    
                    # Sanitize filename
                    if custom_filename:
                        custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename.strip())
                        if not custom_filename:
                            custom_filename = original_name
                    else:
                        custom_filename = original_name
                    
                    additional_custom_filenames[file_idx] = f"{custom_filename}{file_extension}"
                
                with col2:
                    # Show preview filename
                    st.text_input(
                        "Final filename",
                        value=additional_custom_filenames[file_idx],
                        disabled=True,
                        key=f"additional_preview_name_{event_idx}_{file_idx}"
                    )
            
            # Upload button for additional images
            if st.button(f"➕ Add {len(additional_files)} More Image(s)", key=f"upload_additional_images_{event_idx}", type="secondary"):
                try:
                    # Use same directory as existing images
                    if images and images[0].get("local_path"):
                        save_dir = Path("data/events_output") / Path(images[0]["local_path"]).parent
                    else:
                        save_dir = Path("data/events_output")
                    
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save each uploaded file
                    uploaded_count = 0
                    for file_idx, uploaded_file in enumerate(additional_files):
                        final_filename = additional_custom_filenames[file_idx]
                        save_path = save_dir / final_filename
                        
                        # Handle duplicate filenames by adding a number
                        counter = 1
                        original_save_path = save_path
                        while save_path.exists():
                            name_part = original_save_path.stem
                            ext_part = original_save_path.suffix
                            save_path = original_save_path.parent / f"{name_part}_{counter}{ext_part}"
                            counter += 1
                        
                        # Save the file
                        save_path.write_bytes(uploaded_file.getbuffer())
                        
                        # Add to event's images array
                        new_img_obj = {
                            "local_path": str(save_path).replace("data\\", "").replace("data/", ""),
                            "filename": save_path.name,
                            "original_url": "",  # No URL since it's uploaded
                            "source_credit": "User Upload"
                        }
                        event["images"].append(new_img_obj)
                        uploaded_count += 1
                    
                    # Update the events list and save to file
                    events[event_idx] = event
                    Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                    
                    st.success(f"✅ Successfully added {uploaded_count} more image(s) to Event {event_idx + 1}!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error uploading additional images: {str(e)}")

    # After the image loop, check if a slot was deleted for this event
    if st.session_state.get('deleted_image_slot') and st.session_state['deleted_image_slot'][0] == event_idx:
        slot_idx = st.session_state['deleted_image_slot'][1]
        st.info(f"You deleted image {slot_idx + 1}. Upload a new image to replace it:")
        new_img = st.file_uploader(f"Upload replacement for deleted image in Event {event_idx + 1}", type=["jpg","jpeg","png","webp"], key=f"replace_image_{event_idx}_{slot_idx}")
        
        # Add custom filename input when an image is uploaded
        replacement_custom_filename = ""
        if new_img:
            # Get the original filename and extension
            original_name = Path(new_img.name).stem
            file_extension = Path(new_img.name).suffix
            
            replacement_custom_filename = st.text_input(
                f"Custom filename for replacement image (optional)",
                value=original_name,
                help=f"Enter a custom name for the replacement image. Extension '{file_extension}' will be added automatically.",
                key=f"replacement_custom_filename_{event_idx}_{slot_idx}"
            )
            
            # Sanitize filename to remove invalid characters
            if replacement_custom_filename:
                replacement_custom_filename = re.sub(r'[<>:"/\\|?*]', '_', replacement_custom_filename.strip())
                if not replacement_custom_filename:
                    replacement_custom_filename = original_name
            else:
                replacement_custom_filename = original_name
            
            # Add upload button for replacement image
            if st.button(f"Upload Replacement Image", key=f"upload_replacement_{event_idx}_{slot_idx}"):
                # Save to same folder as previous images, or to a default
                if images and images[0].get("local_path"):
                    save_dir = Path("data/events_output") / Path(images[0]["local_path"]).parent
                else:
                    save_dir = Path("data/events_output")
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Use custom filename with original extension
                file_extension = Path(new_img.name).suffix
                final_filename = f"{replacement_custom_filename}{file_extension}"
                save_path = save_dir / final_filename
                
                save_path.write_bytes(new_img.getbuffer())
                # Add to event's images array at the deleted slot
                new_img_obj = {
                    "local_path": str(save_path),
                    "filename": final_filename
                }
                event.setdefault("images", []).insert(slot_idx, new_img_obj)
                events[event_idx] = event
                Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                st.session_state['deleted_image_slot'] = None
                st.success(f"Uploaded and added '{final_filename}' to Event {event_idx + 1}!")
                st.rerun() 