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
        s3_prefix = "s3fs-public/event-activity"
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
            else:
                current_prefix = choice if choice else ""

if __name__ == "__main__":
    s3 = S3()
    s3.run_interactive()

