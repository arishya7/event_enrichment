import streamlit as st
import json
from pathlib import Path
from PIL import Image

# Set the title and a nice header for the app
st.set_page_config(page_title="Event Viewer", layout="wide")
st.title("🎉 Event JSON Viewer")
st.write("Select a JSON file from the `events_output` directory to display its contents.")

# --- Functions ---
def get_json_files(directory: str) -> list:
    """Finds all .json files in the specified directory."""
    p = Path(directory)
    if not p.is_dir():
        return []
    return list(p.glob("*.json"))

def load_json_data(file_path: Path) -> list:
    """Loads and returns the content of a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure data is always a list
            if isinstance(data, dict):
                return [data]
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# --- Main App ---

# Find JSON files in the events_output directory
EVENT_DIR = "events_output"
json_files = get_json_files(EVENT_DIR)

if not json_files:
    st.warning(f"No JSON files found in the `{EVENT_DIR}` directory.")
    st.stop()

# Create a mapping from filename to full path for the selectbox
file_options = {file.name: file for file in json_files}

# --- Sidebar for file selection ---
st.sidebar.header("Select Event File")
selected_file_name = st.sidebar.selectbox(
    "Choose a file to view:",
    options=list(file_options.keys())
)

# --- Display Content ---
if selected_file_name:
    selected_file_path = file_options[selected_file_name]
    st.header(f"Viewing: `{selected_file_name}`")
    
    event_data = load_json_data(selected_file_path)
    
    if not event_data:
        st.error("Could not load or parse the selected JSON file. It might be empty or malformed.")
    else:
        # Create a search bar
        search_query = st.text_input("Search for events by title, description, or venue:", "")
        
        # Filter events based on search query
        filtered_events = []
        if search_query:
            for event in event_data:
                # Check title, description, and venue
                title = event.get('title', '').lower()
                description = event.get('description', '').lower()
                venue = event.get('venue_name', '').lower()
                
                if (search_query.lower() in title or 
                    search_query.lower() in description or
                    search_query.lower() in venue):
                    filtered_events.append(event)
        else:
            filtered_events = event_data
            
        st.write(f"Displaying **{len(filtered_events)}** of **{len(event_data)}** events.")

        # Display events in expanders
        for i, event in enumerate(filtered_events):
            with st.expander(f"**{event.get('title', 'No Title')}** at **{event.get('venue_name', 'No Venue')}**"):
                
                # --- Main Details in Columns ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**🗓️ Date & Time:** {event.get('datetime_display', 'N/A')}")
                    st.markdown(f"**📍 Venue:** {event.get('venue_name', 'N/A')}")
                    st.markdown(f"**🏠 Address:** {event.get('full_address', 'N/A')}")
                
                with col2:
                    st.markdown(f"**💰 Price:** {event.get('price_display', 'N/A')}")
                    st.markdown(f"**👶 Age Group:** {event.get('age_group_display', 'N/A')}")
                    st.markdown(f"**🔗 URL:** [Link]({event.get('url', '#')})")
            
                st.markdown(f"**📝 Description:**")
                st.info(event.get('description', 'No description available.'))
                
                # --- Categories ---
                categories = event.get('categories', [])
                if categories:
                    st.markdown("**🏷️ Categories:**")
                    st.write(", ".join(categories))
            
                
                # Identify fields that are not already explicitly displayed to show them with less emphasis.
                handled_fields = {
                    'title', 'venue_name', 'datetime_display', 'full_address', 
                    'price_display', 'age_group_display', 'url', 
                    'description', 'categories', 'images'
                }
                additional_details = {k: v for k, v in event.items() if k not in handled_fields and v}

                if additional_details:
                    st.markdown("**Additional Details:**")
                    cols = st.columns(3)
                    for idx, (key, value) in enumerate(additional_details.items()):
                        with cols[idx % 3]:
                            st.markdown(f"**{key.replace('_', ' ').title()}:**")
                            st.caption(str(value))
                
                # --- Images ---
                st.markdown("---")
                images = event.get('images', [])
                if images:
                    st.markdown(f"**🖼️ Images ({len(images)}):**")
                    
                    # Create a grid of images
                    cols = st.columns(5) # Display up to 5 images per row
                    for idx, img_info in enumerate(images):
                        img_path = Path(img_info.get('local_path', ''))
                        if img_path.exists():
                            try:
                                image = Image.open(img_path)
                                with cols[idx % 5]:
                                    st.image(image, caption=f"Source: {img_info.get('source_credit', 'N/A')}", use_column_width=True)
                            except Exception as e:
                                with cols[idx % 5]:
                                    st.warning(f"Could not load image: {img_path.name}")
                        else:
                             with cols[idx % 5]:
                                st.warning(f"Image not found at: {str(img_path)}")
                else:
                    st.markdown("**🖼️ No images available for this event.**") 