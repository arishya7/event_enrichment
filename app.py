import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="Event JSON & Image Editor", layout="wide")
st.title("Event JSON & Image Editor")

# Helper to find all event JSON files
def find_event_json_files(base_dir):
    base = Path(base_dir)
    event_files = []
    for folder in base.glob("*/"):
        for json_file in folder.glob("*.json"):
            event_files.append(json_file)
    return event_files

# Helper to get images for an event
def get_event_images(event_folder, blog_source):
    images_dir = event_folder / "images" / blog_source
    if images_dir.exists():
        return list(images_dir.glob("*"))
    return []

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

# 3. Select event from list
event_titles = [e.get("title", f"Event {i}") for i, e in enumerate(events)]
selected_idx = st.selectbox("Select event to edit:", range(len(events)), format_func=lambda i: event_titles[i])
event = events[selected_idx]

# 4. Edit event JSON
event_json_str = st.text_area(
    "Edit selected event JSON (edit and click Save)",
    value=json.dumps(event, indent=2, ensure_ascii=False),
    height=350,
    key=f"event_json_area_{selected_idx}"
)

save_json = st.button("Save Event JSON")
if save_json:
    try:
        updated_event = json.loads(event_json_str)
        events[selected_idx] = updated_event
        Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        st.success("Event JSON saved!")
        event = updated_event
    except Exception as e:
        st.error(f"Invalid JSON: {e}")

# 5. Image management
st.subheader("Event Images")
images = event.get("images", [])
if not images:
    st.info("No images found for this event.")
else:
    for idx, img_obj in enumerate(images):
        local_path = img_obj.get("local_path")
        filename = img_obj.get("filename", Path(local_path).name if local_path else "")
        if not local_path:
            continue
        img_file = Path(local_path)
        cols = st.columns([2, 1, 1])
        with cols[0]:
            if img_file.exists():
                st.image(str(img_file), caption=filename, width=250)
                st.caption(f"File name: {filename}")
            else:
                st.warning(f"Image not found: {img_file}")
        with cols[1]:
            with st.form(f"replace_{img_file}_{idx}"):
                uploaded = st.file_uploader(f"Replace {filename}", type=["jpg","jpeg","png","webp"], key=f"uploader_{img_file}_{idx}")
                submitted = st.form_submit_button("Replace")
                if submitted and uploaded:
                    new_name = uploaded.name
                    new_path = img_file.parent / new_name
                    new_path.write_bytes(uploaded.getbuffer())
                    # Update JSON if file name changes
                    if new_name != img_file.name:
                        img_obj["local_path"] = str(new_path)
                        img_obj["filename"] = new_name
                        if img_file.exists():
                            img_file.unlink()
                    # Overwrite if same name, no JSON change needed
                    Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                    st.success(f"Replaced {filename} with {new_name}")
                    st.experimental_rerun()
        with cols[2]:
            if st.button(f"Delete"):
                # Remove file
                if img_file.exists():
                    img_file.unlink()
                # Remove from images array
                event["images"].pop(idx)
                events[selected_idx] = event
                Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                st.success(f"Deleted {filename}")
                st.experimental_rerun()
    st.markdown("---")
    st.write("Upload a new image:")
    new_img = st.file_uploader("New image", type=["jpg","jpeg","png","webp"], key=f"new_image_{selected_idx}")
    if new_img:
        # Save to same folder as first image, or to a default
        if images and images[0].get("local_path"):
            save_dir = Path("data/events_output") / Path(images[0]["local_path"]).parent
        else:
            save_dir = Path("data/events_output")
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / new_img.name
        save_path.write_bytes(new_img.getbuffer())
        # Add to event's images array
        event.setdefault("images", []).append({
            "local_path": str(save_path),
            "filename": new_img.name
        })
        events[selected_idx] = event
        Path(selected_file).write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        st.success(f"Uploaded and added {new_img.name} to event JSON!")
        st.experimental_rerun() 