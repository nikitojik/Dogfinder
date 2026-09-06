import io
import uuid
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024
THUMB_SIZE = (600, 600)


EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@lru_cache
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def build_object_key(listing_id: int, content_type: str) -> str:
    ext = EXTENSIONS[content_type]
    return f"listings/{listing_id}/{uuid.uuid4().hex}.{ext}"


def build_thumb_key(object_key: str) -> str:
    head, _, tail = object_key.rpartition("/")
    return f"{head}/thumb_{tail}"


def create_upload_url(object_key: str, content_type: str, expires: int = 600) -> str:
    return get_s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )


def get_object_info(object_key: str) -> dict | None:
    try:
        head = get_s3_client().head_object(Bucket=settings.s3_bucket, Key=object_key)
    except ClientError:
        return None
    return {
        "size": head["ContentLength"],
        "content_type": head.get("ContentType", ""),
    }


def download_object(object_key: str) -> bytes:
    obj = get_s3_client().get_object(Bucket=settings.s3_bucket, Key=object_key)
    return obj["Body"].read()


def upload_bytes(object_key: str, data: bytes, content_type: str) -> None:
    get_s3_client().put_object(
        Bucket=settings.s3_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )


def delete_object(object_key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket, Key=object_key)


def public_url(object_key: str) -> str:
    # Бакет открыт на чтение только для локальной разработки.
    # Перед деплоем заменить на presigned GET с ограниченным сроком жизни.
    return f"{settings.s3_endpoint}/{settings.s3_bucket}/{object_key}"


def make_thumbnail(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        return buffer.getvalue()
