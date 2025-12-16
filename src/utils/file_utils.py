import requests
import shutil
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import unquote, urlparse
import re
import json

from src.utils.output_formatter import formatter

def save_to_json(data: List[Any] | Dict[str, Any], file_path: Path, indent: int = 2) -> bool:
    """Save a list of dictionaries to a JSON file.
    
    Args:
        data (List[Dict[str, Any]]): List of dictionaries to save
        file_path (Path): Path where to save the JSON file
        indent (int, optional): Number of spaces for JSON indentation. Defaults to 2.
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR][file_utils.save_to_json] Failed to save data to {file_path}: {str(e)}")
        return False

def download_image(image_urls: List[str], base_file_path: Path) -> List[Dict[str, str]]:
    """Download multiple images from URLs and save them with sequential numbering.
    
    Args:
        image_urls (List[str]): List of image URLs to download
        base_file_path (Path): Base path for saving images (without extension or index)
        
    Returns:
        List[Dict[str, str]]: List of dictionaries for successfully downloaded images.
        Each dictionary contains:
            - local_path: Local filesystem path where the image is stored
            - original_url: Original URL where the image was downloaded from
            - filename: Name of the image file
            - source_credit: Attribution or credit for the image source
    """
    downloaded_images = []
    success_index = 1  # Only increment for successful downloads

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "image",
        "Referer": "https://www.marinabaysands.com/",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    }

    session = requests.Session()
    session.headers.update(headers)
    
    # Allowed image formats
    ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
    ALLOWED_CONTENT_TYPES = ('image/jpeg', 'image/jpg', 'image/png', 'image/webp')
    
    for image_url in image_urls:
        try:
            # Validate URL scheme
            if not urlparse(image_url).scheme in ('http', 'https'):
                continue

            response = session.get(image_url, stream=True, timeout=20)
            response.raise_for_status()

            # Determine file extension from URL
            try:
                parsed_url = urlparse(image_url)
                url_path = Path(unquote(parsed_url.path))
                extension = url_path.suffix.lower() if url_path.suffix else None
            except:
                extension = None
            
            # Check content-type header to determine format
            content_type = response.headers.get('content-type', '')
            ct_lower = content_type.lower().split(';')[0].strip()  # Remove charset, etc.
            
            # Determine final extension from content-type or URL
            final_extension = None
            if ct_lower in ALLOWED_CONTENT_TYPES:
                # Map content-type to extension
                if 'jpeg' in ct_lower or 'jpg' in ct_lower:
                    final_extension = '.jpg'
                elif 'png' in ct_lower:
                    final_extension = '.png'
                elif 'webp' in ct_lower:
                    final_extension = '.webp'
            elif extension and extension in ALLOWED_EXTENSIONS:
                # Use extension from URL if it's allowed
                final_extension = extension
            else:
                # Skip unsupported formats (SVG, GIF, BMP, etc.)
                print(f"│ │ │ [files_utils.download_image] Skipping unsupported format: {image_url} (extension: {extension}, content-type: {ct_lower})")
                continue
            
            # Skip if we still don't have a valid extension
            if not final_extension or final_extension not in ALLOWED_EXTENSIONS:
                print(f"│ │ │ [files_utils.download_image] Skipping unsupported format: {image_url} (extension: {extension}, content-type: {ct_lower})")
                continue

            # Extract source credit from URL
            try:
                parsed_url = urlparse(image_url)
                domain = parsed_url.netloc.lower()
                domain = re.sub(r'^www\.', '', domain)
                domain = re.sub(r'\.(com|org|net|edu|gov|sg|io|co|uk).*$', '', domain)
                source_credit = ' '.join(word.capitalize() for word in re.split(r'[-_]', domain))
            except:
                source_credit = "Unknown Source"
            
            # Create file path with success index (use final_extension determined above)
            file_path = base_file_path.with_name(f"{base_file_path.name}_{success_index}").with_suffix(final_extension)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
                
            result = {
                "local_path": str(file_path).replace("data\\", ""), 
                "original_url": image_url,
                "filename": file_path.name,
                "source_credit": source_credit
            }
            downloaded_images.append(result)
            success_index += 1  # Only increment on successful download

        except requests.exceptions.HTTPError:
            continue
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException as e:
            print(f"│ │ │ [files_utils.download_image] Error downloading image. URL will be skipped \n│ │ │ \tURL: {image_url}\n│ │ │ \tError: {e}")
            continue
        except IOError as e:
            print(f"│ │ │ [files_utils.download_image] IO Error saving image to {base_file_path}_{success_index}: {e}")
            continue
        except Exception as e:
            print(f"│ │ │ [files_utils.download_image] An unexpected error occurred for {image_url}: {e}")
            continue
    
    return downloaded_images

def edit_prompt_interactively(original_prompt: str) -> str:
    """Allow user to edit the prompt interactively using nano.
    
    Args:
        original_prompt (str): The original prompt text
        
    Returns:
        str: The edited prompt text
    """
    # Create simple temp filename
    temp_file_path = "temp_prompt.txt"
    
    try:
        # Create the file with the original prompt
        with open(temp_file_path, 'w', encoding='utf-8') as file:
            file.write(original_prompt)
        
        print(f"\n{'='*60}")
        print("🔧 PROMPT EDITING MODE")
        print(f"{'='*60}")
        print("The prompt has been saved to a temporary file.")
        print("You can now edit it to improve event detection.")
        print(f"File location: {temp_file_path}")
        print("\nPress Enter to open the file in nano for editing...")
        input()
        
        # Open the file in nano for editing
        try:
            subprocess.run(['nano', temp_file_path], check=True)
        except FileNotFoundError:
            print("❌ nano editor not found. Trying with notepad (Windows)...")
            try:
                subprocess.run(['notepad', temp_file_path], check=True)
            except FileNotFoundError:
                print("❌ No suitable text editor found.")
                print("Please edit the file manually and press Enter when done:")
                print(f"File path: {temp_file_path}")
                input()
        
        # Read the edited content
        with open(temp_file_path, 'r', encoding='utf-8') as file:
            edited_prompt = file.read()
        
        # Clean up the file
        os.remove(temp_file_path)
        
        print("✅ Prompt has been updated!")
        print(f"{'='*60}\n")
        
        return edited_prompt
        
    except Exception as e:
        print(f"❌ Error during prompt editing: {str(e)}")
        print("Using original prompt...")
        # Try to clean up the file if it exists
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass
        return original_prompt

def cleanup_temp_folders(feed_dir: Path, articles_output_dir: Path) -> None:
    """Clean up temporary folders with user options to choose what to clean.
    
    Allows user to selectively clean:
    1. Feed directory contents
    2. Articles output directory contents
    3. Individual files within directories
    
    Args:
        feed_dir (Path): Path to the feed directory
        articles_output_dir (Path): Path to the articles output directory
    """
    formatter.print_section("Cleanup Temporary Folders")
    
    # Collect all temp directories and their contents
    temp_locations = []
    
    # Check feed directory
    if feed_dir.exists() and any(feed_dir.iterdir()):
        feed_contents = list(feed_dir.iterdir())
        temp_locations.append({
            'name': 'Feed Directory',
            'path': feed_dir,
            'contents': feed_contents,
            'type': 'directory'
        })
    
    # Check articles output directory  
    if articles_output_dir.exists() and any(articles_output_dir.iterdir()):
        articles_contents = list(articles_output_dir.iterdir())
        temp_locations.append({
            'name': 'Articles Output Directory',
            'path': articles_output_dir,
            'contents': articles_contents,
            'type': 'directory'
        })
    
    if not temp_locations:
        formatter.print_info("No temporary files found to clean")
        formatter.print_section_end()
        return
    
    # Show what's available for cleanup
    formatter.print_info("Found temporary files/folders:")
    for idx, location in enumerate(temp_locations, 1):
        formatter.print_item(f"{idx}. {location['name']}: {location['path']}")
        for content in location['contents']:
            if content.is_file():
                file_size = content.stat().st_size / 1024  # KB
                formatter.print_level1(f"   📄 {content.name} ({file_size:.1f} KB)")
            else:
                sub_files = len(list(content.rglob('*'))) if content.is_dir() else 0
                formatter.print_level1(f"   📁 {content.name}/ ({sub_files} files)")
    
    # Get user choices
    formatter.print_info("Cleanup options:")
    formatter.print_item("A - Clean all temporary folders")
    formatter.print_item("S - Select specific directories to clean")
    formatter.print_item("N - Skip cleanup")
    
    choice = input("| Choose cleanup option (A/S/N): ").strip().upper()
    
    if choice == 'N':
        formatter.print_info("Cleanup skipped")
        formatter.print_section_end()
        return
    elif choice == 'A':
        # Clean everything
        _clean_all_temp_folders(temp_locations)
    elif choice == 'S':
        # Selective cleanup
        _selective_cleanup(temp_locations)
    else:
        formatter.print_warning("Invalid choice, skipping cleanup")
    
    formatter.print_section_end()

def _clean_all_temp_folders(temp_locations: list) -> None:
    """Clean all temporary folders.
    
    Args:
        temp_locations (list): List of temporary location dictionaries
    """
    formatter.print_info("Cleaning all temporary folders...")
    
    for location in temp_locations:
        try:
            if location['path'].exists():
                shutil.rmtree(location['path'])
                formatter.print_success(f"✅ Deleted: {location['name']}")
            else:
                formatter.print_info(f"ℹ️  {location['name']} already clean")
        except Exception as e:
            formatter.print_error(f"❌ Failed to delete {location['name']}: {str(e)}")

def _selective_cleanup(temp_locations: list) -> None:
    """Allow user to select specific directories/files to clean.
    
    Args:
        temp_locations (list): List of temporary location dictionaries
    """
    formatter.print_info("Select directories to clean:")
    
    for idx, location in enumerate(temp_locations, 1):
        formatter.print_item(f"{idx}. {location['name']}")
    
    selection = input("Enter numbers separated by commas (e.g., 1,2): ").strip()
    
    if not selection:
        formatter.print_info("No selection made, skipping cleanup")
        return
    
    try:
        selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]
        
        for idx in selected_indices:
            if 0 <= idx < len(temp_locations):
                location = temp_locations[idx]
                
                # Ask for confirmation for each directory
                confirm = input(f"Delete {location['name']} ({location['path']})? (Y/N): ").strip().upper()
                if confirm == 'Y':
                    try:
                        if location['path'].exists():
                            shutil.rmtree(location['path'])
                            formatter.print_success(f"✅ Deleted: {location['name']}")
                        else:
                            formatter.print_info(f"ℹ️  {location['name']} already clean")
                    except Exception as e:
                        formatter.print_error(f"❌ Failed to delete {location['name']}: {str(e)}")
                else:
                    formatter.print_info(f"Skipped: {location['name']}")
            else:
                formatter.print_warning(f"Invalid selection: {idx + 1}")
                
    except ValueError:
        formatter.print_error("Invalid input format. Use numbers separated by commas.")

def get_next_event_id(tracker_path: str = "data/event_id_tracker.txt") -> int:
    """Read, increment, and return the next event ID from the tracker file."""
    try:
        with open(tracker_path, "r") as f:
            curr = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        curr = 431  # Start before first event
    next_id = curr + 1
    with open(tracker_path, "w") as f:
        f.write(str(next_id))
    return next_id

def update_event_id_tracker(new_curr: int, tracker_path: str = "data/event_id_tracker.txt") -> None:
    """Manually update the event id tracker (rarely needed)."""
    with open(tracker_path, "w") as f:
        f.write(str(new_curr))