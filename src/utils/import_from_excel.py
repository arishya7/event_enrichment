import json
import pandas as pd
import os
from pathlib import Path
from datetime import datetime

def reconstruct_json_event(row):
    """
    Reconstruct the JSON event data from a flattened Excel row.
    Only includes fields that have actual values (not empty).
    """
    event = {}
    
    # Simple fields - only add if not empty
    simple_fields = [
        'title', 'blurb', 'description', 'guid', 'activity_or_event', 'url',
        'price_display', 'price', 'min_price', 'max_price', 'is_free', 'organiser', 'age_group_display',
        'min_age', 'max_age', 'datetime_display', 'start_datetime', 'end_datetime',
        'venue_name', 'scraped_on', 'address_display', 'latitude', 'longitude'
    ]
    
    for field in simple_fields:
        value = row.get(field)
        if pd.notna(value) and str(value).strip():
            event[field] = value
    
    # Handle categories - split back into array if not empty
    categories_str = row.get('categories')
    if pd.notna(categories_str) and str(categories_str).strip():
        categories = [cat.strip() for cat in str(categories_str).split(',') if cat.strip()]
        if categories:
            event['categories'] = categories
    
    # Handle images - reconstruct array from separate columns
    images = []
    for i in range(1, 11):  # Check up to 10 images
        image_data = {}
        
        # Check each image property
        local_path = row.get(f'image_{i}_local_path')
        original_url = row.get(f'image_{i}_original_url')
        filename = row.get(f'image_{i}_filename')
        source_credit = row.get(f'image_{i}_source_credit')
        
        # Only add properties that have values
        if pd.notna(local_path) and str(local_path).strip():
            image_data['local_path'] = local_path
        if pd.notna(original_url) and str(original_url).strip():
            image_data['original_url'] = original_url
        if pd.notna(filename) and str(filename).strip():
            image_data['filename'] = filename
        if pd.notna(source_credit) and str(source_credit).strip():
            image_data['source_credit'] = source_credit
        
        # Only add image to array if it has at least one property
        if image_data:
            images.append(image_data)
        else:
            # If this image slot is empty, we can stop checking further images
            # since they were filled sequentially in the export
            break
    
    # Only add images array if it has content
    if images:
        event['images'] = images
    
    return event

def import_excel_to_json_directory(excel_file_path, output_directory=None):
    """
    Import Excel data with multiple sheets and convert each sheet back to its original JSON file.
    Each sheet is converted to a JSON file with the same name as the sheet.
    
    Args:
        excel_file_path (str): Path to the Excel file to import
        output_directory (str, optional): Directory to save JSON files. If None, uses current directory.
    """
    try:
        print("Starting multi-sheet Excel import process...")
        
        # Validate Excel file exists
        if not os.path.exists(excel_file_path):
            print(f"✗ Excel file not found: {excel_file_path}")
            return
        
        # Set up output directory
        if output_directory is None:
            output_directory = "imported_json_files"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        print(f"Output directory: {output_directory}")
        
        # Read Excel file and get all sheet names
        excel_file = pd.ExcelFile(excel_file_path)
        sheet_names = excel_file.sheet_names
        
        if not sheet_names:
            print("No sheets found in Excel file.")
            return
        
        print(f"Found {len(sheet_names)} sheets: {sheet_names}")
        
        total_events_imported = 0
        successful_imports = 0
        
        for sheet_name in sheet_names:
            print(f"\nProcessing sheet: {sheet_name}")
            
            try:
                # Read data from sheet
                df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
                
                if df.empty:
                    print(f"  No data found in sheet '{sheet_name}'")
                    continue
                
                print(f"  Loaded {len(df)} rows from sheet")
                
                # Process each row and reconstruct JSON objects
                events_data = []
                for index, row in df.iterrows():
                    event_json = reconstruct_json_event(row)
                    if event_json:  # Only add if the event has any data
                        events_data.append(event_json)
                    else:
                        print(f"  Skipped empty row {index + 1}")
                
                if not events_data:
                    print(f"  No valid events found in sheet '{sheet_name}'")
                    continue
                
                # Create JSON filename from sheet name
                json_filename = f"{sheet_name}.json"
                json_file_path = os.path.join(output_directory, json_filename)
                
                # Save to JSON file
                with open(json_file_path, 'w', encoding='utf-8') as file:
                    json.dump(events_data, file, indent=2, ensure_ascii=False)
                
                print(f"  ✓ Exported {len(events_data)} events to: {json_file_path}")
                total_events_imported += len(events_data)
                successful_imports += 1
                
            except Exception as e:
                print(f"  ✗ Error processing sheet '{sheet_name}': {e}")
                continue
        
        print(f"\n✓ Successfully imported {total_events_imported} total events from {successful_imports} sheets.")
        print(f"✓ Created {successful_imports} JSON files in directory: {output_directory}")
        
        return output_directory
        
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def import_excel_to_json(excel_file_path, json_file_path=None, sheet_name='Events'):
    """
    Import Excel data and convert it back to JSON format (single sheet).
    
    Args:
        excel_file_path (str): Path to the Excel file to import
        json_file_path (str, optional): Output JSON file path. If None, auto-generates filename.
        sheet_name (str): Name of the Excel sheet to read from. Default: 'Events'.
    """
    try:
        print("Starting Excel import process...")
        
        # Load Excel data
        print(f"Loading Excel data from: {excel_file_path}")
        if not os.path.exists(excel_file_path):
            print(f"✗ Excel file not found: {excel_file_path}")
            return
        
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        
        if df.empty:
            print("No data found in Excel file.")
            return
        
        print(f"Loaded {len(df)} rows from Excel file.")
        
        # Generate JSON filename if not provided
        if json_file_path is None:
            timestamp = "_".join(Path(excel_file_path).stem.split("_")[-2:])
            json_file_path = f"events_{timestamp}.json"
        
        # Process each row and reconstruct JSON objects
        print("Converting Excel rows to JSON objects...")
        
        events_data = []
        for index, row in df.iterrows():
            event_json = reconstruct_json_event(row)
            if event_json:  # Only add if the event has any data
                events_data.append(event_json)
                title = event_json.get('title', f'Event {index + 1}')
                print(f"Processed row {index + 1}: {title}")
            else:
                print(f"Skipped empty row {index + 1}")
        
        if not events_data:
            print("No valid events found to export.")
            return
        
        # Save to JSON file
        print(f"Saving {len(events_data)} events to JSON file...")
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(events_data, file, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully imported {len(events_data)} events from Excel.")
        print(f"✓ JSON file saved as: {json_file_path}")
        
        return json_file_path
        
    except FileNotFoundError:
        print(f"✗ Excel file not found: {excel_file_path}")
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Import events data from Excel file and convert to JSON format."""
    
    print("Excel Import Tool")
    print("=================")
    print("1. Import single sheet to JSON file")
    print("2. Import all sheets to separate JSON files")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        # Single sheet import
        excel_file_path = input("Enter Excel file path: ").strip()
        if not os.path.exists(excel_file_path):
            print(f"✗ File not found: {excel_file_path}")
            return
        
        sheet_name = input("Enter sheet name (default: 'Events'): ").strip()
        if not sheet_name:
            sheet_name = 'Events'
        
        import_excel_to_json(excel_file_path, sheet_name=sheet_name)
    
    elif choice == "2":
        # Multi-sheet import
        excel_file_path = input("Enter Excel file path: ").strip()
        if not os.path.exists(excel_file_path):
            print(f"✗ File not found: {excel_file_path}")
            return
        
        output_directory = input("Enter output directory (default: 'imported_json_files'): ").strip()
        if not output_directory:
            output_directory = "imported_json_files"
        
        import_excel_to_json_directory(excel_file_path, output_directory)
    
    else:
        print("Invalid choice. Please select 1 or 2.")

if __name__ == "__main__":
    main() 