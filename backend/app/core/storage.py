import uuid
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class ObjectStorage:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint,
            region_name=settings.object_storage_region,
            aws_access_key_id=settings.object_storage_access_key,
            aws_secret_access_key=settings.object_storage_secret_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=2,
                read_timeout=2,
                retries={"max_attempts": 1, "mode": "standard"},
            ),
        )

    def check_ready(self) -> None:
        """Verify that the configured media bucket is reachable with current credentials."""
        self._client.head_bucket(Bucket=settings.object_storage_bucket)

    def create_property_upload(self, property_id: uuid.UUID, content_type: str) -> tuple[str, str]:
        extension = _ALLOWED_IMAGE_TYPES.get(content_type)
        if extension is None:
            raise ValueError("Only JPEG, PNG and WebP property images are supported")

        object_key = f"properties/{property_id}/{uuid.uuid4()}.{extension}"
        upload_url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.object_storage_bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.media_upload_expiry_seconds,
        )
        return object_key, upload_url

    def object_exists(self, object_key: str) -> bool:
        try:
            self._client.head_object(Bucket=settings.object_storage_bucket, Key=object_key)
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def delete(self, object_key: str) -> None:
        self._client.delete_object(Bucket=settings.object_storage_bucket, Key=object_key)

    def public_url(self, object_key: str) -> str:
        safe_key = quote(object_key, safe="/")
        return f"{settings.object_storage_public_base_url.rstrip('/')}/{safe_key}"


storage = ObjectStorage()
