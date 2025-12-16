import json
import pandas as pd
import os
import subprocess
import platform
from pathlib import Path
import glob

def flatten_json_event(event_data):
    """
    Flatten the JSON event data into a single row format.
    Handles arrays for categories and images (up to 10 images).
    """
    flattened = {}
    
    # Simple fields
    simple_fields = [
        'title', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
        'price_display', 'price', 'min_price', 'max_price', 'is_free', 'organiser', 'age_group_display',
        'min_age', 'max_age', 'datetime_display', 'start_datetime', 'end_datetime',
        'venue_name', 'scraped_on', 'address_display', 'latitude', 'longitude'
    ]
    
    for field in simple_fields:
        flattened[field] = event_data.get(field, '')
    
    # Handle categories array - join with semicolon
    categories = event_data.get('categories', [])
    flattened['categories'] = ', '.join(categories) if categories else ''
    
    # Handle images array - create separate columns for up to 10 images
    images = event_data.get('images', [])
    
    # Create columns for each image (up to 10 images)
    for i in range(10):
        if i < len(images):
            # Image exists, extract its properties
            image = images[i]
            flattened[f'image_{i+1}_local_path'] = image.get('local_path', '')
            flattened[f'image_{i+1}_original_url'] = image.get('original_url', '')
            flattened[f'image_{i+1}_filename'] = image.get('filename', '')
            flattened[f'image_{i+1}_source_credit'] = image.get('source_credit', '')
        else:
            # No more images, fill with empty values
            flattened[f'image_{i+1}_local_path'] = ''
            flattened[f'image_{i+1}_original_url'] = ''
            flattened[f'image_{i+1}_filename'] = ''
            flattened[f'image_{i+1}_source_credit'] = ''
    
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

def export_directory_to_excel(json_directory, excel_file_path=None, auto_open=True):
    """
    Export all JSON files from a directory to a single Excel file with multiple sheets.
    Each JSON file becomes a separate sheet named after the JSON filename.
    
    Args:
        json_directory (str): Path to directory containing JSON files
        excel_file_path (str, optional): Output Excel file path. If None, auto-generates filename.
        auto_open (bool): Whether to automatically open the Excel file after creation. Default: True.
    """
    try:
        print("Starting multi-file Excel export process...")
        
        # Validate directory exists
        if not os.path.exists(json_directory):
            print(f"✗ Directory not found: {json_directory}")
            return
        
        # Find all JSON files in directory
        json_pattern = os.path.join(json_directory, "*.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            print(f"✗ No JSON files found in directory: {json_directory}")
            return
        
        print(f"Found {len(json_files)} JSON files in directory.")
        
        # Generate Excel filename if not provided
        if excel_file_path is None:
            timestamp = Path(json_directory).name
            excel_file_path = f"events_export_{timestamp}.xlsx"
        
        # Create Excel writer object
        with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
            total_events = 0
            
            for json_file_path in sorted(json_files):
                # Get filename without extension for sheet name
                sheet_name = Path(json_file_path).stem
                
                print(f"\nProcessing: {json_file_path}")
                
                # Load JSON data
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as file:
                        events_data = json.load(file)
                    
                    if not events_data:
                        print(f"  No events data found in {json_file_path}")
                        continue
                    
                    print(f"  Loaded {len(events_data)} events")
                    
                    # Process each event and create a list of dictionaries
                    processed_events = []
                    for i, event in enumerate(events_data):
                        flattened_event = flatten_json_event(event)
                        processed_events.append(flattened_event)
                    
                    # Create DataFrame
                    df = pd.DataFrame(processed_events)
                    
                    # Export to Excel sheet
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Get the worksheet and auto-adjust column widths
                    worksheet = writer.sheets[sheet_name]
                    for column_cells in worksheet.columns:
                        length = max(len(str(cell.value or '')) for cell in column_cells)
                        worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
                    
                    total_events += len(events_data)
                    print(f"  ✓ Exported {len(events_data)} events to sheet '{sheet_name}'")
                    
                except json.JSONDecodeError:
                    print(f"  ✗ Invalid JSON format in file: {json_file_path}")
                    continue
                except Exception as e:
                    print(f"  ✗ Error processing {json_file_path}: {e}")
                    continue
        
        print(f"\n✓ Successfully exported {total_events} total events from {len(json_files)} JSON files.")
        print(f"✓ Excel file saved as: {excel_file_path}")
        print(f"✓ Created {len(json_files)} sheets in the Excel file.")
        
        # Auto-open the Excel file if requested
        if auto_open:
            open_excel_file(excel_file_path)
        
        return excel_file_path
        
    except ImportError as e:
        print(f"✗ Missing required library. Install with: pip install pandas openpyxl")
        print(f"Error: {e}")
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

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
            _filename = Path(json_file_path).parent.name
            excel_file_path = f"events_export_{_filename}.xlsx"
        
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

def main(auto_open=False):
    """Export events data to Excel - supports both single files and directories."""
    
    print("Excel Export Tool")
    print("=================")
    print("1. Export single JSON file")
    print("2. Export all JSON files from directory")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        # Single file export
        json_file_path = input("Enter JSON file path: ").strip()
        if os.path.exists(json_file_path):
            export_json_to_excel(json_file_path, auto_open=auto_open)
        else:
            print(f"✗ File not found: {json_file_path}")
    
    elif choice == "2":
        # Directory export
        json_directory = input("Enter directory path containing JSON files: ").strip()
        if os.path.exists(json_directory):
            export_directory_to_excel(json_directory, auto_open=auto_open)
        else:
            print(f"✗ Directory not found: {json_directory}")
    
    else:
        print("Invalid choice. Please select 1 or 2.")

if __name__ == "__main__":
    main() 