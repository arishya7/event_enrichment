import boto3
import os
import json

# Get AWS credentials from environment variables
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")

if not all([aws_access_key, aws_secret_key]):
    print("Error: AWS credentials not found in environment variables")
    print("Please make sure you have AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY set")
    exit(1)

def view_file_content(s3_client, file_path):
    """View the content of a specific file in the bucket"""
    bucket = 'mummysmarket-assets-dev'
    
    try:
        print(f"\nViewing file: s3://{bucket}/{file_path}")
        print("="*50)
        
        # Get the object
        response = s3_client.get_object(Bucket=bucket, Key=file_path)
        content = response['Body'].read()
        
        # Try to decode as text
        try:
            # First try UTF-8
            text_content = content.decode('utf-8')
            
            # Check if it's JSON and format it nicely
            if file_path.lower().endswith('.json'):
                try:
                    json_data = json.loads(text_content)
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(text_content)
            else:
                # For other text files, show first 2000 characters
                if len(text_content) > 2000:
                    print(text_content[:2000])
                    print(f"\n... (showing first 2000 characters of {len(text_content)} total)")
                else:
                    print(text_content)
                    
        except UnicodeDecodeError:
            # If it's not text, show file info instead
            print("This appears to be a binary file. Cannot display content as text.")
            print(f"File size: {len(content)} bytes")
            print(f"Content type: {response.get('ContentType', 'Unknown')}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"Error reading file content: {str(e)}")

def list_directory_contents(s3_client, prefix=''):
    """List contents of a specific directory (prefix) in the bucket"""
    bucket = 'mummysmarket-assets-dev'
    
    # Ensure prefix ends with '/' if not empty
    if prefix and not prefix.endswith('/'):
        prefix += '/'
    
    print(f"\nListing contents of: s3://{bucket}/{prefix or ''}")
    print("="*50)
    found_objects = False
    
    try:
        # List objects with the given prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
            # Handle subdirectories
            if 'CommonPrefixes' in page:
                found_objects = True
                print("\n📁 Folders:")
                for common_prefix in page['CommonPrefixes']:
                    dir_name = common_prefix['Prefix']
                    print(f"   {dir_name}")
            
            # Handle files
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
            print(f"\nNo contents found in: s3://{bucket}/{prefix or ''}")
        
        print("\nNavigation:")
        print("- Enter a folder path to explore (e.g., 's3fs-private/events_output/')")
        print("- Press Enter for root directory")
        print("- Type '..' to go up one level")
        print("- Type 'view <filename>' to view file content (e.g., 'view events.json')")
        print("- Type 'q' to quit")
        
    except Exception as e:
        print(f"Error listing directory contents: {str(e)}")

if __name__ == "__main__":
    try:
        # Initialize S3 client
        s3 = boto3.client('s3',
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key,
                        region_name=aws_region
                        )
        
        current_prefix = ""
        
        while True:
            # List current directory contents
            list_directory_contents(s3, current_prefix)
            
            # Get next directory to check
            choice = input("\nEnter path> ").strip()
            
            if choice.lower() == 'q':
                print("\nGoodbye!")
                break
            elif choice == '..':
                # Go up one level
                current_prefix = os.path.dirname(current_prefix.rstrip('/'))
                if current_prefix:
                    current_prefix += '/'
            elif choice.lower().startswith('view '):
                # View file content
                filename = choice[5:].strip()  # Remove 'view ' prefix
                if filename:
                    # Construct full file path
                    file_path = current_prefix + filename if current_prefix else filename
                    view_file_content(s3, file_path)
                else:
                    print("Please specify a filename to view (e.g., 'view events.json')")
            else:
                # Update current prefix
                current_prefix = choice if choice else ""

    except Exception as e:
        print(f"Error accessing S3: {str(e)}")
