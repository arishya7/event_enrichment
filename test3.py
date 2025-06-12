import boto3
import os
s3 = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
    )

s3.meta.client.upload_file(
    Filename='test.txt',
    Bucket='mummysmarket-assets-dev',
    Key='s3fs-private'
)


