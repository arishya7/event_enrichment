import boto3
import os

# Get AWS credentials from environment variables
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")

if not all([aws_access_key, aws_secret_key]):
    print("Error: AWS credentials not found in environment variables")
    print("Please make sure you have AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY set")
    exit(1)

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
            else:
                # Update current prefix
                current_prefix = choice if choice else ""

    except Exception as e:
        print(f"Error accessing S3: {str(e)}")
