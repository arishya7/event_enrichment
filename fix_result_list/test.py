import json
import datetime
from address_extractor import extract_venue_details
from image_extractor import search_images, download_image
import os
from pathlib import Path
from dotenv import load_dotenv
import re

def sanitize_filename(filename):
    # Remove invalid characters and limit length
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length to 100 characters (including extension)
    if len(filename) > 100:
        base, ext = os.path.splitext(filename)
        filename = base[:96] + ext  # 96 + 4 for extension = 100
    return filename

def process_events():
    # Load environment variables
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("cx")

    if not google_api_key or not cx:
        print("Error: Missing required environment variables (GOOGLE_API_KEY or cx)")
        return

    try:
        # Read the input JSON file
        with open("result_list.json", "r", encoding="utf-8") as f:
            events = json.load(f)
    except FileNotFoundError:
        print("Error: result_list.json not found")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON in result_list.json")
        return

    # Create images directory if it doesn't exist
    images_dir = Path("./images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Get current timestamp
    current_timestamp = datetime.datetime.now().isoformat()

    # Process every 20th event
    processed_events = []
    for i, event in enumerate(events):
        if i % 20 == 0:  # Process only every 20th event
            print(f"Processing event {i} of {len(events)}")
            
            # Add timestamp
            event['scraped_on'] = current_timestamp
            
            # Extract venue details
            try:
                event = extract_venue_details(event, google_api_key)
            except Exception as e:
                print(f"Error extracting venue details for event {i}: {e}")

            # Search and download images
            try:
                # Skip if no title
                if not event.get('title'):
                    print(f"Skipping image search for event {i}: No title found")
                    processed_events.append(event)
                    continue

                image_results = search_images(
                    query=event['title'],
                    api_key=google_api_key,
                    cx=cx,
                    num_results=5,
                    site_to_search=event.get('url', 'NULL')
                )

                if image_results:
                    downloaded_images = []
                    for idx, image_item in enumerate(image_results, 1):
                        # Skip invalid URLs
                        if not image_item['link'].startswith(('http://', 'https://')):
                            print(f"Skipping invalid URL: {image_item['link']}")
                            continue

                        # Create sanitized filename
                        base_filename = sanitize_filename(f"{event['title']}_{idx}")
                        img_file_path = images_dir / base_filename
                        
                        try:
                            download_result = download_image(image_item['link'], img_file_path)
                            if download_result:
                                downloaded_images.append(download_result)
                        except Exception as e:
                            print(f"    Error downloading image {image_item['link']}: {str(e)}")
                            continue

                    if downloaded_images:
                        event['images'] = downloaded_images
                    else:
                        print(f"No images successfully downloaded for event {i}")
                else:
                    print(f"No image results found for event {i}")
            except Exception as e:
                print(f"Error processing images for event {i}: {e}")

        processed_events.append(event)

    # Save the processed events back to a new file
    output_file = "processed_result_list.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_events, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved processed events to {output_file}")
    except Exception as e:
        print(f"Error saving processed events: {e}")

if __name__ == "__main__":
    process_events()
