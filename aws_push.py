import boto3
from pathlib import Path
import os 

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
bucket = os.getenv('S3_BUCKET_NAME')
s3_prefix = os.getenv('S3_SUBFOLDER')
print(bucket)
print(s3_prefix)
def upload_directory(local_path):
    s3_prefix = 's3fs-private'
    for path in local_path.rglob('*'):
        if path.is_file():
            # Compute the S3 key
            relative_path = path.relative_to(local_path)
            s3_key = f"{s3_prefix}/{relative_path.as_posix()}"
            print(f"Uploading {path} to s3://{bucket}/{s3_key}")
            s3.upload_file(str(path), bucket, s3_key)

def upload_file(local_path):
    s3_key = f"{s3_prefix}/{local_path.name}"
    print(f"Uploading {local_path} to s3://{bucket}/{s3_key}")
    s3.upload_file(str(local_path), bucket, s3_key)

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Upload a single file")
    print("2. Upload a directory")
    print("Any other key to quit")
    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == '1':
        file_path = input("Enter the file path (e.g., events_total/events_1.json): ").strip()
        upload_file(Path(file_path))
    elif choice == '2':
        timestamp = input("Enter the timestamp (e.g., 20250613_100921): ").strip()
        subfolder_name = f'events_output/{timestamp}'
        local_dir = Path(subfolder_name)
        upload_directory(local_dir)
    else:
        print("Goodbye!")
        quit()
