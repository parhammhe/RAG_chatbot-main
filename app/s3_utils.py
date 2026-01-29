"""
S3 utilities - upload and retrieve PDFs from AWS S3.
"""
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    """Create and return an S3 client."""
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )


def upload_pdf_to_s3(file_bytes: bytes, filename: str, user_id: int) -> str:
    """
    Upload a PDF file to S3.
    
    Args:
        file_bytes: The PDF file content as bytes
        filename: Original filename
        user_id: The owner's user ID
        
    Returns:
        The S3 key where the file was stored
    """
    s3_client = get_s3_client()
    
    # Generate unique S3 key: users/{user_id}/{uuid}_{filename}
    unique_id = str(uuid.uuid4())[:8]
    s3_key = f"users/{user_id}/{unique_id}_{filename}"
    
    s3_client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType="application/pdf"
    )
    
    return s3_key


def get_pdf_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for downloading a PDF.
    
    Args:
        s3_key: The S3 key of the file
        expiration: URL expiration time in seconds (default 1 hour)
        
    Returns:
        Presigned URL string, or None if error
    """
    s3_client = get_s3_client()
    
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_S3_BUCKET,
                "Key": s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError:
        return None


def delete_pdf_from_s3(s3_key: str) -> bool:
    """
    Delete a PDF file from S3.
    
    Args:
        s3_key: The S3 key of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    s3_client = get_s3_client()
    
    try:
        s3_client.delete_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key
        )
        return True
    except ClientError:
        return False
