import streamlit as st
import json
from pathlib import Path
from PIL import Image
from collections import defaultdict

# Set the title and a nice header for the app
st.set_page_config(page_title="Event & Article Viewer", layout="wide")
st.title("🎉 Event & Article Viewer")

# --- Functions ---
def get_subdirectories(directory: str) -> list:
    """Find all subdirectories in the specified directory."""
    p = Path(directory)
    if not p.is_dir():
        return []
    return [d for d in p.iterdir() if d.is_dir()]

def get_json_files(directory: Path) -> list:
    """Finds all .json files in the specified directory."""
    if not directory.is_dir():
        return []
    return list(directory.glob("*.json"))

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
    
def clean_text(text: str) -> str:
    """Clean text for markdown display"""
    return text.replace("$", "\$").replace("(", "\(").replace(")", "\)").replace("!","\!").replace("#","\#").replace("*","\*")

def display_event_images(event, event_dir):
    """Display images for an event, combining event directory path with image paths"""
    images = event.get('images', [])
    if images:
        st.markdown(f"**🖼️ Images ({len(images)}):**")
        
        # Create a grid of images
        cols = st.columns(5) # Display up to 5 images per row
        for idx, img_info in enumerate(images):
            # Combine event directory with image path
            relative_path = img_info.get('local_path', '').replace('\\', '/')
            img_path = Path(relative_path)
            
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

def display_events_in_directory(directory: Path):
    """Display events from JSON files in the given directory"""
    json_files = get_json_files(directory)
    
    if not json_files:
        st.warning(f"No JSON files found in `{directory}`.")
        st.warning(f"It is currently in process of extracting events from the articles. Please check back later.")
        return
    
    # Create a mapping from filename to full path for the selectbox
    file_options = {file.name: file for file in json_files}
    
    # --- Sidebar for file selection ---
    with st.sidebar:
        st.header(f"Select Event File: {directory.name}")
        selected_file_name = st.selectbox(
            "Choose a file to view:",
            options=list(file_options.keys()),
            key=f"file_selector_{directory.name}"
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
            search_query = st.text_input(
                "Search for events by title, description, or venue:", 
                "", 
                key=f"search_{directory.name}"
            )
            
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
            for event in filtered_events:
                with st.expander(f"**{event.get('title')}**"):
                    # --- Main Details in Columns ---
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Date & Time:** {clean_text(event.get('datetime_display', 'N/A'))}")
                        st.write(f"**Venue:** {clean_text(event['venue_name'] if event.get('venue_name') else 'N/A')}")
                        st.write(f"**Address:** {clean_text(event['full_address'] if event.get('full_address') else 'N/A')}")
                    
                    with col2:
                        st.write(f"**Price:** {clean_text(event.get('price_display', 'N/A'))}")
                        st.write(f"**Age Group:** {clean_text(event.get('age_group_display', 'N/A'))}")
                        st.write(f"**URL:** {clean_text(event.get('url', 'N/A'))}")
                
                    st.markdown(f"**Description:**")
                    st.info(clean_text(event.get('description', 'N/A')))
                    
                    # --- Categories ---
                    st.markdown("-"*100)
                    categories = event.get('categories', [])
                    if categories:
                        st.markdown("**Categories:**")
                        st.write(", ".join(categories))
                
                    # Identify fields that are not already explicitly displayed
                    handled_fields = {
                        'title', 'venue_name', 'datetime_display', 'full_address', 
                        'price_display', 'age_group_display', 'url', 
                        'description', 'categories', 'images'
                    }
                    additional_details = {k: v for k, v in event.items() if k not in handled_fields and v}
                    st.markdown("-"*100)
                    if additional_details:
                        st.markdown("**Additional Details:**")
                        cols = st.columns(3)
                        for idx, (key, value) in enumerate(additional_details.items()):
                            with cols[idx % 3]:
                                st.markdown(f"**{key.replace('_', ' ').title()}:**")
                                st.caption(str(value))
                
                    # --- Images ---
                    st.markdown("---")
                    display_event_images(event, directory)

# --- Main App ---
# Get all subdirectories in events_output
EVENT_DIR = Path("events_output")
subdirs = get_subdirectories("events_output")

if not subdirs:
    st.warning("No subdirectories found in events_output.")
else:
    # Create tabs dynamically based on subdirectories
    tabs = st.tabs([subdir.name for subdir in subdirs])
    
    # Display content for each tab
    for tab, subdir in zip(tabs, subdirs):
        with tab:
            display_events_in_directory(subdir) 