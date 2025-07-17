import boto3
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from src.utils.config import config

@dataclass
class S3:
    bucket: str = field(init=False)
    region: str = field(init=False)
    aws_access_key: str = field(init=False)
    aws_secret_key: str = field(init=False)
    s3: object = field(init=False)

    def __post_init__(self):
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
        s3_prefix = "s3fs-public/event-activity"
        local_path = Path(local_path)
        if base_dir is None:
            base_dir = local_path.parent
        else:
            base_dir = Path(base_dir)
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

