import boto3
import os 
from pathlib import Path

from src.utils.config import config

s3 = boto3.client(
    's3',
    aws_access_key_id=config.aws_access_key_id,
    aws_secret_access_key=config.aws_secret_access_key
)
bucket = os.getenv('S3_BUCKET_NAME')

def upload_directory(local_path, base_dir=None):
    """Upload directory to S3, preserving directory structure relative to the base directory.
    
    Args:
        local_path (Path): Local directory path to upload
        base_dir (Path, optional): Base directory to calculate relative path from.
                                  If None, uses the directory's parent.
    """
    s3_prefix = "s3fs-public/event-activity"
    local_path = Path(local_path)
    
    # Determine base directory for relative path calculation
    if base_dir is None:
        base_dir = local_path.parent
    else:
        base_dir = Path(base_dir)
    
    for path in local_path.rglob('*'):
        if path.is_file():
            try:
                # Calculate relative path from the base directory
                relative_path = path.relative_to(base_dir)
                # Convert to forward slashes for S3
                relative_path_str = str(relative_path).replace("\\", "/")
                s3_key = f"{s3_prefix}/{relative_path_str}"
                print(f"Uploading {path} to s3://{bucket}/{s3_key}")
                s3.upload_file(str(path), bucket, s3_key)
            except ValueError:
                # If path is not relative to base_dir, skip it or use alternative approach
                print(f"Warning: {path} is not relative to {base_dir}, skipping...")
                continue

def upload_file(local_path, base_dir=None):
    """Upload single file to S3.
    
    Args:
        local_path (Path): Local file path to upload
        base_dir (Path, optional): Base directory to calculate relative path from. 
                                  If None, uses the file's parent directory.
    """
    s3_prefix = "s3fs-private/event-activity"
    local_path = Path(local_path)
    
    if base_dir:
        # Calculate relative path from the specified base directory
        base_dir = Path(base_dir)
        try:
            relative_path = local_path.relative_to(base_dir)
            relative_path_str = str(relative_path).replace("\\", "/")
            s3_key = f"{s3_prefix}/{relative_path_str}"
        except ValueError:
            # If local_path is not relative to base_dir, just use filename
            s3_key = f"{s3_prefix}/{local_path.name}"
    else:
        # Default behavior: just use the filename
        s3_key = f"{s3_prefix}/{local_path.name}"
    
    print(f"Uploading {local_path} to s3://{bucket}/{s3_key}")
    s3.upload_file(str(local_path), bucket, s3_key)

