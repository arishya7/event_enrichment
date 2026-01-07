"""
Deduplicate Events Across 2026 Folders

This script:
1. Finds all folders starting with "2026" in data/events_output/
2. Loads all JSON event files from those folders
3. Identifies duplicates across folders using semantic similarity
4. Removes duplicates from their original JSON files
5. Deletes images associated with removed duplicates
6. Keeps original folder structure (no merging)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.run import Run
from src.core.event import Event


def find_2026_folders(events_output_dir: Path) -> List[Path]:
    """Find all folders starting with '2026' in events_output directory."""
    folders = []
    if not events_output_dir.exists():
        return folders
    
    for item in events_output_dir.iterdir():
        if item.is_dir() and item.name.startswith('2026'):
            folders.append(item)
    
    return sorted(folders)


def find_all_folders(events_output_dir: Path) -> List[Path]:
    """Find all folders in events_output directory."""
    folders = []
    if not events_output_dir.exists():
        return folders
    
    for item in events_output_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):  # Skip hidden folders
            folders.append(item)
    
    return sorted(folders)


def select_folders_interactive(events_output_dir: Path) -> List[Path]:
    """Interactive folder selection."""
    all_folders = find_all_folders(events_output_dir)
    
    if not all_folders:
        print("❌ No folders found in data/events_output/")
        return []
    
    print("\n📂 Available folders:")
    for i, folder in enumerate(all_folders, 1):
        print(f"   {i}. {folder.name}")
    print()
    
    # Default: select all 2026 folders
    default_folders = [f for f in all_folders if f.name.startswith('2026')]
    if default_folders:
        print(f"💡 Default: All 2026 folders ({len(default_folders)} folders)")
        print()
    
    while True:
        try:
            choice = input("Select folders:\n"
                         "  [Enter] = Use default (all 2026 folders)\n"
                         "  'all' = All folders\n"
                         "  Numbers = Specific folders (e.g., '1,3,5' or '1-5')\n"
                         "  Custom = Type folder names separated by commas\n"
                         "Your choice: ").strip()
            
            if not choice:
                # Default: all 2026 folders
                return default_folders if default_folders else []
            
            if choice.lower() == 'all':
                return all_folders
            
            # Check if it's numbers
            if choice.replace(',', '').replace('-', '').replace(' ', '').isdigit() or ',' in choice or '-' in choice:
                selected = []
                # Handle ranges like "1-5" or comma-separated like "1,3,5"
                parts = choice.replace(' ', '').split(',')
                for part in parts:
                    if '-' in part:
                        # Range
                        start, end = part.split('-', 1)
                        try:
                            start_idx = int(start) - 1
                            end_idx = int(end)
                            for idx in range(start_idx, end_idx):
                                if 0 <= idx < len(all_folders):
                                    selected.append(all_folders[idx])
                        except ValueError:
                            print(f"Invalid range: {part}")
                            continue
                    else:
                        # Single number
                        try:
                            idx = int(part) - 1
                            if 0 <= idx < len(all_folders):
                                selected.append(all_folders[idx])
                            else:
                                print(f"Invalid number: {part}")
                        except ValueError:
                            print(f"Invalid number: {part}")
                            continue
                
                if selected:
                    return selected
                else:
                    print("No valid folders selected. Please try again.")
                    continue
            
            # Check if it's folder names
            folder_names = [name.strip() for name in choice.split(',')]
            selected = []
            for name in folder_names:
                # Try exact match first
                found = None
                for folder in all_folders:
                    if folder.name == name or folder.name.startswith(name):
                        found = folder
                        break
                
                if found:
                    selected.append(found)
                else:
                    print(f"⚠️ Folder not found: {name}")
            
            if selected:
                return selected
            else:
                print("No valid folders found. Please try again.")
                continue
                
        except KeyboardInterrupt:
            print("\nCancelled.")
            return []
        except Exception as e:
            print(f"Error: {e}. Please try again.")
            continue


class EventWithSource:
    """Container for event with its source file information."""
    def __init__(self, event: Event, source_file: Path, source_folder: Path, event_index: int):
        self.event = event
        self.source_file = source_file  # JSON file path
        self.source_folder = source_folder  # Folder containing the JSON
        self.event_index = event_index  # Index in the JSON array
        self.is_duplicate = False
        self.kept_by_event = None  # Reference to the event we're keeping instead


def load_all_events_with_sources(folders: List[Path]) -> List[EventWithSource]:
    """Load all events from all folders with their source file information."""
    all_events = []
    
    for folder in folders:
        # Look for JSON files directly in folder
        for json_file in folder.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    events_list = data if isinstance(data, list) else [data]
                    
                    for idx, event_dict in enumerate(events_list):
                        try:
                            # Set skip_url_validation to avoid API calls during loading
                            event_dict['skip_url_validation'] = True
                            event = Event.from_dict(event_dict)
                            all_events.append(EventWithSource(event, json_file, folder, idx))
                        except Exception as e:
                            continue
            except Exception as e:
                continue
        
        # Look in relevant/ subdirectory
        relevant_dir = folder / "relevant"
        if relevant_dir.exists():
            for json_file in relevant_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        events_list = data if isinstance(data, list) else [data]
                        
                        for idx, event_dict in enumerate(events_list):
                            try:
                                # Set skip_url_validation to avoid API calls during loading
                                event_dict['skip_url_validation'] = True
                                event = Event.from_dict(event_dict)
                                all_events.append(EventWithSource(event, json_file, folder, idx))
                            except Exception as e:
                                continue
                except Exception as e:
                    continue
        
        # Look in non-relevant/ subdirectory
        nonrelevant_dir = folder / "non-relevant"
        if nonrelevant_dir.exists():
            for json_file in nonrelevant_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        events_list = data if isinstance(data, list) else [data]
                        
                        for idx, event_dict in enumerate(events_list):
                            try:
                                # Set skip_url_validation to avoid API calls during loading
                                event_dict['skip_url_validation'] = True
                                event = Event.from_dict(event_dict)
                                all_events.append(EventWithSource(event, json_file, folder, idx))
                            except Exception as e:
                                continue
                except Exception as e:
                    continue
    
    return all_events


def find_duplicates_semantic(events_with_sources: List[EventWithSource], run: Run, sim_threshold: float = 0.85) -> List[EventWithSource]:
    """
    Find duplicates within the batch using semantic similarity.
    Compares all events against each other and keeps the first occurrence of each duplicate group.
    """
    if not events_with_sources or len(events_with_sources) <= 1:
        return []
    
    events = [ews.event for ews in events_with_sources]
    
    # Use Run's within-batch deduplication to find which events to keep
    # This compares events within the batch, not against database
    kept_events = run._deduplicate_within_batch(events, sim_threshold=sim_threshold)
    kept_set = {id(evt) for evt in kept_events}
    
    # Mark events as duplicates if they weren't kept
    duplicates = []
    for ews in events_with_sources:
        if id(ews.event) not in kept_set:
            ews.is_duplicate = True
            duplicates.append(ews)
    
    return duplicates


def get_image_paths_from_event(event: Event, source_folder: Path) -> List[Path]:
    """Get all image file paths associated with an event."""
    image_paths = []
    
    if not event.images:
        return image_paths
    
    images_dir = source_folder / "images"
    if not images_dir.exists():
        return image_paths
    
    for img_dict in event.images:
        img_url = img_dict.get('url', '')
        if not img_url:
            continue
        
        # Extract filename from URL
        parsed_url = urlparse(img_url)
        filename = Path(parsed_url.path).name
        
        # Try to find the image file in images directory
        # Could be in subdirectories too
        for img_file in images_dir.rglob(filename):
            image_paths.append(img_file)
        
        # Also check for filename with different extensions or variations
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            for img_file in images_dir.rglob(f"{base_name}{ext}"):
                if img_file not in image_paths:
                    image_paths.append(img_file)
    
    return image_paths


def remove_duplicates_from_files(events_with_sources: List[EventWithSource], duplicates: List[EventWithSource]) -> Dict[str, Any]:
    """Remove duplicate events from their source JSON files and delete associated images."""
    stats = {
        'files_modified': 0,
        'events_removed': 0,
        'images_deleted': 0,
        'errors': []
    }
    
    # Group duplicates by source file
    duplicates_by_file: Dict[Path, List[EventWithSource]] = {}
    for dup in duplicates:
        if dup.source_file not in duplicates_by_file:
            duplicates_by_file[dup.source_file] = []
        duplicates_by_file[dup.source_file].append(dup)
    
    # Process each file
    for json_file, file_duplicates in duplicates_by_file.items():
        try:
            # Load the file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            events_list = data if isinstance(data, list) else [data]
            
            # Get indices to remove (in reverse order to maintain indices)
            indices_to_remove = sorted([dup.event_index for dup in file_duplicates], reverse=True)
            
            # Delete images for duplicates
            for dup in file_duplicates:
                image_paths = get_image_paths_from_event(dup.event, dup.source_folder)
                for img_path in image_paths:
                    try:
                        if img_path.exists():
                            img_path.unlink()
                            stats['images_deleted'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Failed to delete {img_path}: {e}")
            
            # Remove events from list
            removed_count = 0
            for idx in indices_to_remove:
                if 0 <= idx < len(events_list):
                    events_list.pop(idx)
                    removed_count += 1
            
            if removed_count > 0:
                # Save the modified file
                output_data = events_list if isinstance(data, list) else (events_list[0] if events_list else {})
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
                
                stats['files_modified'] += 1
                stats['events_removed'] += removed_count
                print(f"   ✅ Removed {removed_count} duplicate(s) from {json_file.name}")
        
        except Exception as e:
            stats['errors'].append(f"Failed to process {json_file}: {e}")
            print(f"   ❌ Error processing {json_file.name}: {e}")
    
    return stats


def main():
    """Main function to deduplicate across 2026 folders."""
    print("\n" + "="*60)
    print("🔍 DEDUPLICATE EVENTS ACROSS 2026 FOLDERS")
    print("="*60)
    print("This will remove duplicates from their original folders and delete associated images.")
    print("Original folder structure will be preserved.\n")
    
    # Confirmation
    confirm = input("Continue? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Setup paths
    base_dir = Path(__file__).parent.parent
    events_output_dir = base_dir / "data" / "events_output"
    
    # Select folders to deduplicate
    print("\n📂 Select folders to deduplicate...")
    folders = select_folders_interactive(events_output_dir)
    
    if not folders:
        print("❌ No folders selected.")
        return
    
    print(f"✅ Found {len(folders)} folders:")
    for folder in folders:
        print(f"   - {folder.name}")
    
    # Load all events with source information
    print("\n📄 Loading events from all folders...")
    all_events_with_sources = load_all_events_with_sources(folders)
    
    print(f"✅ Loaded {len(all_events_with_sources)} total events")
    
    # Count per folder
    folder_counts = {}
    for ews in all_events_with_sources:
        folder_name = ews.source_folder.name
        folder_counts[folder_name] = folder_counts.get(folder_name, 0) + 1
    
    print("\n📊 Events per folder:")
    for folder_name, count in sorted(folder_counts.items()):
        print(f"   {folder_name}: {count} events")
    
    # Deduplicate using Run class
    print("\n🔍 Finding duplicates using semantic similarity...")
    run = Run(timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"), blog_name=None)
    run.setup_directories()
    
    duplicates = find_duplicates_semantic(all_events_with_sources, run, sim_threshold=0.85)
    
    print(f"\n✅ Found {len(duplicates)} duplicate events to remove")
    
    if not duplicates:
        print("No duplicates found. Nothing to remove.")
        return
    
    # Show what will be removed
    print("\n📋 Duplicates to be removed:")
    duplicates_by_folder = {}
    for dup in duplicates:
        folder_name = dup.source_folder.name
        if folder_name not in duplicates_by_folder:
            duplicates_by_folder[folder_name] = []
        duplicates_by_folder[folder_name].append(dup)
    
    for folder_name, folder_dups in sorted(duplicates_by_folder.items()):
        print(f"\n   {folder_name}: {len(folder_dups)} duplicate(s)")
        for dup in folder_dups[:5]:  # Show first 5
            print(f"      - {dup.event.title[:50]}... @ {dup.source_file.name}")
        if len(folder_dups) > 5:
            print(f"      ... and {len(folder_dups) - 5} more")
    
    # Final confirmation
    print(f"\n⚠️  This will remove {len(duplicates)} events and delete associated images.")
    final_confirm = input("Proceed with removal? (yes/no): ").strip().lower()
    if final_confirm not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Remove duplicates from files and delete images
    print("\n🗑️  Removing duplicates from files...")
    stats = remove_duplicates_from_files(all_events_with_sources, duplicates)
    
    # Print summary
    print("\n" + "="*60)
    print("✅ DEDUPLICATION COMPLETE")
    print("="*60)
    print(f"📄 Files modified: {stats['files_modified']}")
    print(f"🗑️  Events removed: {stats['events_removed']}")
    print(f"🖼️  Images deleted: {stats['images_deleted']}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"   - {error}")
    
    print("="*60)


if __name__ == "__main__":
    main()
