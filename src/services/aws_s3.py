"""
AWS S3 Service for File Storage and Management

This module provides a comprehensive interface for interacting with Amazon S3 storage.
It handles file uploads, directory operations, content viewing, and interactive
browsing of S3 buckets.

The S3 class is designed to work with the application's specific bucket structure:
- s3fs-public/event-activity: Public files accessible via web
- s3fs-private/event-activity: Private files for internal use

Features:
- Upload individual files or entire directories
- View file contents with automatic format detection
- Interactive directory browsing
- Automatic path handling and error recovery
- Support for both public and private file storage

Dependencies:
- boto3: AWS SDK for Python
- pathlib: Path manipulation
- dataclasses: Data class definitions
- json: JSON file handling

Example Usage:
    s3 = S3()
    s3.upload_file("local_file.json")
    s3.list_directory_contents("s3fs-public/")
    s3.run_interactive()  # Start interactive browser
"""

import boto3
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from src.utils.config import config

@dataclass
class S3:
    """
    AWS S3 client for file storage and management operations.
    
    This class provides a high-level interface for S3 operations including:
    - File and directory uploads
    - Content viewing and browsing
    - Interactive file system navigation
    
    The class automatically initializes with credentials from the config module
    and provides methods for both public and private file storage.
    
    Attributes:
        bucket (str): S3 bucket name for file storage
        region (str): AWS region for the S3 bucket
        aws_access_key (str): AWS access key for authentication
        aws_secret_key (str): AWS secret key for authentication
        s3 (boto3.client): Boto3 S3 client instance
    """
    bucket: str = field(init=False)
    region: str = field(init=False)
    aws_access_key: str = field(init=False)
    aws_secret_key: str = field(init=False)
    s3: object = field(init=False)

    def __post_init__(self):
        """
        Initialize S3 client with credentials from config.
        
        Sets up the boto3 S3 client with proper authentication and region
        configuration. Uses fallback values for bucket and region if not
        specified in config.
        """
        self.bucket = getattr(config, 's3_bucket', 'mummysmarket-assets-dev')
        self.region = getattr(config, 'aws_region', None)
        self.aws_access_key = config.aws_access_key_id
        self.aws_secret_key = config.aws_secret_access_key
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region
        )

    def upload_directory(self, local_path, base_dir=None):
        """
        Upload an entire directory structure to S3.
        
        Recursively uploads all files in a directory while preserving the
        directory structure. Files are uploaded to the public s3fs-public
        prefix for web accessibility.
        
        Args:
            local_path (str or Path): Path to the local directory to upload
            base_dir (str or Path, optional): Base directory for relative path calculation.
                If None, uses the parent of local_path.
                
        Example:
            s3.upload_directory("data/events_output/", "data/")
            # Uploads files to s3fs-public/event-activity/events_output/
        """
        s3_prefix = "s3fs-private/events_output"
        local_path = Path(local_path)
        if base_dir is None:
            base_dir = local_path.parent
        else:
            base_dir = Path(base_dir)
        
        # Recursively find and upload all files
        for path in local_path.rglob('*'):
            if path.is_file():
                try:
                    relative_path = path.relative_to(base_dir)
                    relative_path_str = str(relative_path).replace("\\", "/")
                    s3_key = f"{s3_prefix}/{relative_path_str}"
                    print(f"Uploading {path} to s3://{self.bucket}/{s3_key}")
                    self.s3.upload_file(str(path), self.bucket, s3_key)
                except ValueError:
                    print(f"Warning: {path} is not relative to {base_dir}, skipping...")
                    continue

    def upload_file(self, local_path, base_dir=None):
        """
        Upload a single file to S3.
        
        Uploads a file to the private s3fs-private prefix for secure storage.
        The file path in S3 is determined by the base_dir parameter.
        
        Args:
            local_path (str or Path): Path to the local file to upload
            base_dir (str or Path, optional): Base directory for relative path calculation.
                If provided, creates relative path; otherwise uses filename only.
                
        Example:
            s3.upload_file("data/events.json", "data/")
            # Uploads to s3fs-private/event-activity/events.json
        """
        s3_prefix = "s3fs-private/event-activity"
        local_path = Path(local_path)
        if base_dir:
            base_dir = Path(base_dir)
            try:
                relative_path = local_path.relative_to(base_dir)
                relative_path_str = str(relative_path).replace("\\", "/")
                s3_key = f"{s3_prefix}/{relative_path_str}"
            except ValueError:
                s3_key = f"{s3_prefix}/{local_path.name}"
        else:
            s3_key = f"{s3_prefix}/{local_path.name}"
        print(f"Uploading {local_path} to s3://{self.bucket}/{s3_key}")
        self.s3.upload_file(str(local_path), self.bucket, s3_key)

    def view_file_content(self, file_path):
        """
        Display the contents of a file stored in S3.
        
        Attempts to read and display file contents with automatic format detection.
        Handles text files, JSON files, and binary files appropriately.
        
        Args:
            file_path (str): S3 key path to the file to view
            
        Features:
            - Automatic JSON formatting for .json files
            - Text truncation for large files (>2000 chars)
            - Binary file detection and size reporting
            - Error handling for missing or inaccessible files
        """
        try:
            print(f"\nViewing file: s3://{self.bucket}/{file_path}")
            print("="*50)
            response = self.s3.get_object(Bucket=self.bucket, Key=file_path)
            content = response['Body'].read()
            
            try:
                text_content = content.decode('utf-8')
                if file_path.lower().endswith('.json'):
                    try:
                        json_data = json.loads(text_content)
                        print(json.dumps(json_data, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(text_content)
                else:
                    if len(text_content) > 2000:
                        print(text_content[:2000])
                        print(f"\n... (showing first 2000 characters of {len(text_content)} total)")
                    else:
                        print(text_content)
            except UnicodeDecodeError:
                print("This appears to be a binary file. Cannot display content as text.")
                print(f"File size: {len(content)} bytes")
                print(f"Content type: {response.get('ContentType', 'Unknown')}")
            print("\n" + "="*50)
        except Exception as e:
            print(f"Error reading file content: {str(e)}")

    def list_directory_contents(self, prefix=''):
        """
        List the contents of an S3 directory with detailed information.
        
        Displays both folders and files in the specified S3 prefix with
        metadata including file sizes and modification dates.
        
        Args:
            prefix (str): S3 prefix to list contents for (default: root)
            
        Features:
            - Separate display of folders and files
            - File size in KB
            - Last modified timestamps
            - Navigation instructions
            - Pagination support for large directories
        """
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        print(f"\nListing contents of: s3://{self.bucket}/{prefix or ''}")
        print("="*50)
        found_objects = False
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter='/'):
                if 'CommonPrefixes' in page:
                    found_objects = True
                    print("\n📁 Folders:")
                    for common_prefix in page['CommonPrefixes']:
                        dir_name = common_prefix['Prefix']
                        print(f"   {dir_name}")
                if 'Contents' in page:
                    found_objects = True
                    files_printed = False
                    for obj in page['Contents']:
                        if obj['Key'] != prefix:
                            if not files_printed:
                                print("\n📄 Files:")
                                files_printed = True
                            key = obj['Key']
                            relative_key = key[len(prefix):] if prefix else key
                            size = obj['Size']
                            last_modified = obj['LastModified']
                            print(f"\n   === {relative_key} ===")
                            print(f"   Size: {size/1024:.2f} KB")
                            print(f"   Last Modified: {last_modified}")
            if not found_objects:
                print(f"\nNo contents found in: s3://{self.bucket}/{prefix or ''}")
            print("\nNavigation:")
            print("- Enter a folder path to explore (e.g., 's3fs-private/events_output/')")
            print("- Press Enter for root directory")
            print("- Type '..' to go up one level")
            print("- Type 'view <filename>' to view file content (e.g., 'view events.json')")
            print("- Type 'q' to quit")
        except Exception as e:
            print(f"Error listing directory contents: {str(e)}")

    def list_files_in_folder(self, folder_prefix):
        """
        List all files in an S3 folder/prefix.
        
        Args:
            folder_prefix (str): S3 prefix/folder path to list
            
        Returns:
            tuple: (success: bool, files: List[Dict], message: str)
            files contains dicts with 'Key' and 'Size' keys
        """
        # Normalize the prefix - convert Windows backslashes to forward slashes
        folder_prefix = folder_prefix.strip().replace('\\', '/')
        
        if not folder_prefix.startswith('s3fs-'):
            # If it's just a timestamp (no slashes), check root folder first
            if '/' not in folder_prefix:
                # Try root folder first (where files actually are)
                folder_prefix = f"s3fs-private/events_output/{folder_prefix}/"
            elif 'images' not in folder_prefix.lower() and not folder_prefix.endswith('/'):
                # If it's a full path but missing trailing slash, add it
                folder_prefix += '/'
            elif 'images' in folder_prefix.lower():
                # Already has images/, just ensure trailing slash
                if not folder_prefix.endswith('/'):
                    folder_prefix += '/'
            else:
                # Full path provided, just ensure it ends with /
                if not folder_prefix.endswith('/'):
                    folder_prefix += '/'
        else:
            # Full S3 path provided, just normalize
            if not folder_prefix.endswith('/'):
                folder_prefix += '/'
        
        print(f"🔍 Searching in: s3://{self.bucket}/{folder_prefix}")
        
        try:
            files = []
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=folder_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'Key': obj['Key'],
                            'Size': obj['Size'],
                            'LastModified': obj.get('LastModified', '')
                        })
            return True, files, f"Found {len(files)} file(s)"
        except Exception as e:
            return False, [], f"Error listing files: {str(e)}"

    def delete_selected_files(self, file_keys, confirm=True, dry_run=False):
        """
        Delete specific files from S3 by their keys.
        
        Args:
            file_keys (List[str]): List of S3 object keys to delete
            confirm (bool): If True, requires confirmation before deletion
            dry_run (bool): If True, only shows what would be deleted
            
        Returns:
            tuple: (success: bool, message: str, deleted_count: int)
        """
        if not file_keys:
            return True, "✅ No files selected for deletion.", 0
        
        if dry_run:
            print(f"\n🔍 [DRY RUN] Would delete {len(file_keys)} file(s):")
            for i, key in enumerate(file_keys, 1):
                print(f"   {i}. {key}")
            return True, f"✅ [DRY RUN] Would delete {len(file_keys)} file(s)", len(file_keys)
        
        if confirm:
            print(f"\n⚠️  WARNING: This will delete {len(file_keys)} file(s):")
            for i, key in enumerate(file_keys[:10], 1):
                print(f"   {i}. {key}")
            if len(file_keys) > 10:
                print(f"   ... and {len(file_keys) - 10} more")
            response = input("\nType 'DELETE' to confirm: ").strip()
            if response != 'DELETE':
                return False, "❌ Deletion cancelled.", 0
        
        # Delete in batches
        deleted_count = 0
        batch_size = 1000
        errors = []
        
        print(f"\n🗑️  Deleting {len(file_keys)} file(s) in batches...")
        for i in range(0, len(file_keys), batch_size):
            batch = [{'Key': key} for key in file_keys[i:i + batch_size]]
            batch_num = (i // batch_size) + 1
            total_batches = (len(file_keys) + batch_size - 1) // batch_size
            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} files)...")
            
            try:
                response = self.s3.delete_objects(
                    Bucket=self.bucket,
                    Delete={'Objects': batch, 'Quiet': False}
                )
                if 'Deleted' in response:
                    deleted_count += len(response['Deleted'])
                    print(f"      ✅ Deleted {len(response['Deleted'])} file(s)")
                
                if 'Errors' in response and response['Errors']:
                    print(f"      ⚠️  {len(response['Errors'])} error(s) occurred:")
                    for error in response['Errors']:
                        error_key = error.get('Key', 'Unknown')
                        error_code = error.get('Code', 'Unknown')
                        error_message = error.get('Message', 'Unknown error')
                        error_msg = f"      ❌ {error_key}"
                        error_msg += f"\n         Code: {error_code}"
                        error_msg += f"\n         Message: {error_message}"
                        errors.append(error_msg)
                        print(error_msg)
            except Exception as e:
                error_msg = f"❌ Exception during deletion: {str(e)}"
                print(f"      {error_msg}")
                return False, error_msg, deleted_count
        
        if errors:
            error_summary = f"❌ Deletion completed with {len(errors)} error(s). Deleted {deleted_count}/{len(file_keys)} files."
            if len(errors) <= 5:
                error_summary += f"\n\nErrors:\n" + "\n".join(errors)
            else:
                error_summary += f"\n\nFirst 5 errors:\n" + "\n".join(errors[:5])
                error_summary += f"\n... and {len(errors) - 5} more errors"
            return False, error_summary, deleted_count
        
        return True, f"✅ Successfully deleted {deleted_count} file(s)", deleted_count

    def delete_folder(self, folder_prefix, confirm=True, dry_run=False):
        """
        Delete a folder (prefix) and all its contents from S3.
        
        In S3, folders are just prefixes. This method deletes all objects
        that start with the given prefix. Supports pagination for large folders.
        
        Args:
            folder_prefix (str): S3 prefix/folder path to delete (e.g., "s3fs-private/events_output/images/")
            confirm (bool): If True, requires confirmation before deletion (default: True)
            dry_run (bool): If True, only shows what would be deleted without actually deleting (default: False)
            
        Returns:
            tuple: (success: bool, message: str, deleted_count: int)
            
        Example:
            success, message, count = s3.delete_folder("s3fs-private/events_output/images/")
            # Deletes all files under the images/ folder
            
            success, message, count = s3.delete_folder("s3fs-private/events_output/images/", dry_run=True)
            # Shows what would be deleted without actually deleting
        """
        # Normalize the prefix - ensure it doesn't have leading/trailing issues
        folder_prefix = folder_prefix.strip()
        
        # If it's just a timestamp, assume it's under events_output
        if not folder_prefix.startswith('s3fs-'):
            # Assume it's a timestamp folder, construct full path
            if '/' not in folder_prefix:
                folder_prefix = f"s3fs-private/events_output/{folder_prefix}/images/"
            else:
                folder_prefix = f"s3fs-private/events_output/{folder_prefix}"
        
        # Ensure prefix ends with / for folder deletion
        if folder_prefix and not folder_prefix.endswith('/'):
            folder_prefix += '/'
        
        if dry_run:
            print(f"🔍 [DRY RUN] Looking for folder: s3://{self.bucket}/{folder_prefix}")
        else:
            print(f"🔍 Looking for folder: s3://{self.bucket}/{folder_prefix}")
        
        try:
            # List all objects with this prefix
            objects_to_delete = []
            paginator = self.s3.get_paginator('list_objects_v2')
            
            try:
                for page in paginator.paginate(Bucket=self.bucket, Prefix=folder_prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            objects_to_delete.append({'Key': obj['Key']})
            except Exception as list_error:
                error_msg = str(list_error)
                if "AccessDenied" in error_msg or "403" in error_msg:
                    return False, f"❌ Access denied. Check your AWS credentials and bucket permissions.", 0
                elif "NoSuchBucket" in error_msg:
                    return False, f"❌ Bucket '{self.bucket}' does not exist.", 0
                else:
                    return False, f"❌ Error listing objects: {error_msg}", 0
            
            if not objects_to_delete:
                # Try to check if the prefix exists at all
                print(f"⚠️  No objects found with prefix: {folder_prefix}")
                print(f"💡 Checking if folder exists...")
                
                # Try listing parent directory to see if folder exists
                parent_prefix = '/'.join(folder_prefix.rstrip('/').split('/')[:-1]) + '/'
                parent_objects = []
                try:
                    for page in paginator.paginate(Bucket=self.bucket, Prefix=parent_prefix, Delimiter='/'):
                        if 'CommonPrefixes' in page:
                            for prefix in page['CommonPrefixes']:
                                if prefix['Prefix'] == folder_prefix:
                                    return True, f"✅ Folder '{folder_prefix}' exists but is empty.", 0
                except:
                    pass
                
                return True, f"✅ Folder '{folder_prefix}' is already empty or doesn't exist.", 0
            
            # Show what would be deleted
            if dry_run:
                print(f"\n🔍 [DRY RUN] Would delete {len(objects_to_delete)} object(s) from:")
                print(f"   s3://{self.bucket}/{folder_prefix}")
                print(f"\n📋 All files that would be deleted:")
                for i, obj in enumerate(objects_to_delete, 1):
                    print(f"   {i}. {obj['Key']}")
                if len(objects_to_delete) > 20:
                    print(f"\n   ... (showing all {len(objects_to_delete)} files)")
                return True, f"✅ [DRY RUN] Would delete {len(objects_to_delete)} object(s) from '{folder_prefix}'", len(objects_to_delete)
            
            # Confirm deletion
            if confirm:
                print(f"\n⚠️  WARNING: This will delete {len(objects_to_delete)} object(s) from:")
                print(f"   s3://{self.bucket}/{folder_prefix}")
                print(f"\n📋 Sample files to be deleted (first 5):")
                for obj in objects_to_delete[:5]:
                    print(f"   - {obj['Key']}")
                if len(objects_to_delete) > 5:
                    print(f"   ... and {len(objects_to_delete) - 5} more")
                
                response = input("\nType 'DELETE' to confirm: ").strip()
                if response != 'DELETE':
                    return False, "❌ Deletion cancelled.", 0
            
            # Delete objects in batches (S3 allows up to 1000 objects per delete request)
            deleted_count = 0
            batch_size = 1000
            errors = []
            
            print(f"\n🗑️  Deleting {len(objects_to_delete)} object(s) in batches of {batch_size}...")
            
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(objects_to_delete) + batch_size - 1) // batch_size
                print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} objects)...")
                
                try:
                    response = self.s3.delete_objects(
                        Bucket=self.bucket,
                        Delete={
                            'Objects': batch,
                            'Quiet': False
                        }
                    )
                    
                    # Count successfully deleted objects
                    if 'Deleted' in response:
                        deleted_count += len(response['Deleted'])
                    
                    # Collect errors
                    if 'Errors' in response and response['Errors']:
                        for error in response['Errors']:
                            error_msg = f"Error deleting {error['Key']}: {error.get('Message', 'Unknown error')} (Code: {error.get('Code', 'Unknown')})"
                            errors.append(error_msg)
                            print(f"   ⚠️  {error_msg}")
                except Exception as delete_error:
                    error_msg = str(delete_error)
                    if "AccessDenied" in error_msg or "403" in error_msg:
                        return False, f"❌ Access denied when deleting. Check your AWS credentials and bucket permissions.", 0
                    else:
                        return False, f"❌ Error during deletion: {error_msg}", 0
            
            if errors:
                return False, f"❌ Deletion completed with {len(errors)} error(s). Deleted {deleted_count}/{len(objects_to_delete)} objects. Errors: {', '.join(errors[:3])}", deleted_count
            
            return True, f"✅ Successfully deleted {deleted_count} object(s) from '{folder_prefix}'", deleted_count
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return False, f"❌ Error deleting folder: {str(e)}\nDetails: {error_details}", 0

    def run_interactive(self):
        """
        Start an interactive S3 file browser.
        
        Provides a command-line interface for browsing S3 contents, viewing files,
        and navigating the directory structure. Supports common file system
        operations like cd, ls, and cat.
        
        Commands:
            - Enter path: Navigate to directory
            - '..': Go up one directory level
            - 'view <filename>': Display file contents
            - 'delete <folder>': Delete a folder and all its contents
            - 'q': Quit the browser
            - Enter: Show current directory contents
        """
        current_prefix = ""
        while True:
            self.list_directory_contents(current_prefix)
            choice = input("\nEnter path> ").strip()
            if choice.lower() == 'q':
                print("\nGoodbye!")
                break
            elif choice == '..':
                current_prefix = os.path.dirname(current_prefix.rstrip('/'))
                if current_prefix:
                    current_prefix += '/'
            elif choice.lower().startswith('view '):
                filename = choice[5:].strip()
                if filename:
                    file_path = current_prefix + filename if current_prefix else filename
                    self.view_file_content(file_path)
                else:
                    print("Please specify a filename to view (e.g., 'view events.json')")
            elif choice.lower().startswith('delete '):
                folder_path = choice[7:].strip()
                if folder_path:
                    full_prefix = current_prefix + folder_path if current_prefix else folder_path
                    success, message, count = self.delete_folder(full_prefix, confirm=True)
                    print(f"\n{message}")
                else:
                    print("Please specify a folder path to delete (e.g., 'delete images/')")
            else:
                current_prefix = choice if choice else ""

if __name__ == "__main__":
    s3 = S3()
    s3.run_interactive()

