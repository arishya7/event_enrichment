import json
import pandas as pd
import os
import subprocess
import platform
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

def open_excel_file(excel_file_path):
    """
    Open the Excel file with the default application (Microsoft Excel).
    """
    try:
        system = platform.system()
        if system == "Windows":
            # On Windows, use os.startfile()
            os.startfile(excel_file_path)
            print(f"✓ Opened Excel file: {excel_file_path}")
        elif system == "Darwin":  # macOS
            subprocess.run(["open", excel_file_path])
            print(f"✓ Opened Excel file: {excel_file_path}")
        elif system == "Linux":
            subprocess.run(["xdg-open", excel_file_path])
            print(f"✓ Opened Excel file: {excel_file_path}")
        else:
            print(f"✓ Excel file created: {excel_file_path}")
            print("  (Auto-open not supported on this platform)")
    except Exception as e:
        print(f"✓ Excel file created: {excel_file_path}")
        print(f"  (Could not auto-open: {e})")

def export_json_to_excel(json_file_path, excel_file_path=None, auto_open=True):
    """
    Export flattened JSON data to Excel file using pandas.
    
    Args:
        json_file_path (str): Path to the JSON file to convert
        excel_file_path (str, optional): Output Excel file path. If None, auto-generates filename.
        auto_open (bool): Whether to automatically open the Excel file after creation. Default: True.
    """
    try:
        print("Starting Excel export process...")
        
        # Load JSON data
        print(f"Loading JSON data from: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as file:
            events_data = json.load(file)
        
        if not events_data:
            print("No events data found in JSON file.")
            return
        
        print(f"Loaded {len(events_data)} events from JSON file.")
        
        # Generate Excel filename if not provided
        if excel_file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_file_path = f"events_export_{timestamp}.xlsx"
        
        # Prepare data for export
        print("Preparing data for export...")
        
        # Process each event and create a list of dictionaries
        processed_events = []
        for i, event in enumerate(events_data):
            flattened_event = flatten_json_event(event)
            processed_events.append(flattened_event)
            print(f"Processed event {i+1}: {event.get('title', 'Unknown title')}")
        
        # Create DataFrame
        df = pd.DataFrame(processed_events)
        
        # Export to Excel with formatting
        with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Events', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Events']
            
            # Auto-adjust column widths
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value or '')) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
        
        print(f"✓ Successfully exported {len(events_data)} events to Excel file.")
        print(f"✓ Excel file saved as: {excel_file_path}")
        print(f"✓ You can open this file in Excel or upload it to Google Sheets.")
        
        # Auto-open the Excel file if requested
        if auto_open:
            open_excel_file(excel_file_path)
        
        return excel_file_path
        
    except FileNotFoundError:
        print(f"✗ JSON file not found: {json_file_path}")
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON format in file: {json_file_path}")
    except ImportError as e:
        print(f"✗ Missing required library. Install with: pip install pandas openpyxl")
        print(f"Error: {e}")
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def main(auto_open=True):
    """Export the Skoolopedia events data to Excel and optionally auto-open it."""
    json_file_path = "data/events_output/20250709_130810/skoolopedia.json"
    export_json_to_excel(json_file_path, auto_open=auto_open)

if __name__ == "__main__":
    main() 