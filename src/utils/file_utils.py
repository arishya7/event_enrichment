import requests
import shutil
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import unquote, urlparse
import re
import json

def save_to_json(data: List[Any] | Dict[str, Any], filepath: Path, indent: int = 2) -> bool:
    """Save a list of dictionaries to a JSON file.
    
    Args:
        data (List[Dict[str, Any]]): List of dictionaries to save
        filepath (Path): Path where to save the JSON file
        indent (int, optional): Number of spaces for JSON indentation. Defaults to 2.
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR][file_utils.save_to_json] Failed to save data to {filepath}: {str(e)}")
        return False

def download_image(image_url: str, filepathwithout_ext: Path) -> Dict[str, str]:
    """Download an image from a URL and save it to the specified path.
    
    Args:
        image_url (str): URL of the image to download
        filepath_without_ext (Path): Path where the image should be saved, without extension
        
    Returns:
        Dict[str, str]: Dictionary containing image metadata or empty dict if download fails.
        The dictionary contains:
            - local_path: Local filesystem path where the image is stored
            - original_url: Original URL where the image was downloaded from
            - filename: Name of the image file
            - source_credit: Attribution or credit for the image source
    """
    try:
        # Validate URL scheme
        if not urlparse(image_url).scheme in ('http', 'https'):
            return {}

        response = requests.get(image_url, stream=True, timeout=20)
        response.raise_for_status()

        # Extract source credit from URL
        try:
            parsed_url = urlparse(image_url)
            domain = parsed_url.netloc.lower()
            domain = re.sub(r'^www\.', '', domain)
            domain = re.sub(r'\.(com|org|net|edu|gov|sg|io|co|uk).*$', '', domain)
            source_credit = ' '.join(word.capitalize() for word in re.split(r'[-_]', domain))
        except:
            source_credit = "Unknown Source"

        # Determine file extension from URL or content-type
        try:
            parsed_url = urlparse(image_url)
            url_path = Path(unquote(parsed_url.path))
            extension = url_path.suffix.lower() if url_path.suffix else '.jpg'
        except:
            extension = '.jpg'
        
        # Check content-type header to refine extension
        content_type = response.headers.get('content-type')
        if content_type:
            ct_lower = content_type.lower()
            if 'jpeg' in ct_lower and extension != ".jpg": 
                extension = ".jpg"
            elif 'png' in ct_lower and extension != ".png": 
                extension = ".png"
            elif 'gif' in ct_lower and extension != ".gif": 
                extension = ".gif"
            elif 'webp' in ct_lower and extension != ".webp": 
                extension = ".webp"
        
        # Add extension to filepath_without_ext
        filepath = filepathwithout_ext.with_suffix(extension)
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
            
        result = {
            "local_path": str(filepath), 
            "original_url": image_url,
            "filename": filepath.name,
            "source_credit": source_credit
        }
        return result

    except requests.exceptions.HTTPError:
        return {}
    except requests.exceptions.Timeout:
        return {}
    except requests.exceptions.RequestException as e:
        print(f"│ │ │ [files_utils.download_image] Error downloading image. URL will be skipped \n\tURL: {image_url}\n\tError: {e}")
        return {}
    except IOError as e:
        print(f"│ │ │ [files_utils.download_image] IO Error saving image to {filepathwithout_ext}: {e}")
        return {}
    except Exception as e:
        print(f"│ │ │ [files_utils.download_image] An unexpected error occurred for {image_url}: {e}")
        return {}

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
