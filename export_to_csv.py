import json
import csv
from datetime import datetime

def flatten_json_event(event_data):
    """
    Flatten the JSON event data into a single row format.
    Handles arrays for categories and images (up to 10 images).
    """
    flattened = {}
    
    # Simple fields
    simple_fields = [
        'title', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
        'price_display', 'price', 'is_free', 'organiser', 'age_group_display',
        'min_age', 'max_age', 'datetime_display', 'start_datetime', 'end_datetime',
        'venue_name', 'scraped_on', 'full_address', 'latitude', 'longitude'
    ]
    
    for field in simple_fields:
        flattened[field] = event_data.get(field, '')
    
    # Handle categories array - join with semicolon
    categories = event_data.get('categories', [])
    flattened['categories'] = '; '.join(categories) if categories else ''
    
    # Handle images array - create separate columns for up to 10 images
    images = event_data.get('images', [])
    for i in range(10):
        flattened[f'image_{i+1}'] = images[i] if i < len(images) else ''
    
    return flattened

def get_headers():
    """Get the column headers for the flattened data."""
    headers = [
        'title', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
        'price_display', 'price', 'is_free', 'organiser', 'age_group_display',
        'min_age', 'max_age', 'datetime_display', 'start_datetime', 'end_datetime',
        'venue_name', 'categories', 'scraped_on', 'full_address', 'latitude', 'longitude'
    ]
    
    # Add image columns
    for i in range(10):
        headers.append(f'image_{i+1}')
    
    return headers

def export_json_to_csv(json_file_path, csv_file_path=None):
    """
    Export flattened JSON data to CSV file.
    """
    try:
        print("Starting CSV export process...")
        
        # Load JSON data
        print(f"Loading JSON data from: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as file:
            events_data = json.load(file)
        
        if not events_data:
            print("No events data found in JSON file.")
            return
        
        print(f"Loaded {len(events_data)} events from JSON file.")
        
        # Generate CSV filename if not provided
        if csv_file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file_path = f"events_export_{timestamp}.csv"
        
        # Prepare data for export
        print("Preparing data for export...")
        headers = get_headers()
        
        # Create CSV file
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write headers
            writer.writerow(headers)
            print("Headers written to CSV.")
            
            # Process each event
            for i, event in enumerate(events_data):
                flattened_event = flatten_json_event(event)
                row = [str(flattened_event.get(header, '')) for header in headers]
                writer.writerow(row)
                print(f"Processed event {i+1}: {event.get('title', 'Unknown title')}")
        
        print(f"✓ Successfully exported {len(events_data)} events to CSV file.")
        print(f"✓ CSV file saved as: {csv_file_path}")
        print(f"✓ You can now import this CSV file into Google Sheets manually.")
        
        return csv_file_path
        
    except FileNotFoundError:
        print(f"✗ JSON file not found: {json_file_path}")
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON format in file: {json_file_path}")
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Export the Skoolopedia events data to CSV."""
    json_file_path = "data/events_output/20250709_130810/skoolopedia.json"
    export_json_to_csv(json_file_path)

if __name__ == "__main__":
    main() 