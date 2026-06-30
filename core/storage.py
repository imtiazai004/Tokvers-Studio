"""
Cloudflare R2 (S3-compatible) object storage adapter.

All generated media (videos, audio, character images) lives here, not on local
disk. The DB stores only the object `key`; files are served via signed URLs.
A 48h lifecycle rule auto-deletes old objects (the DB record survives).
"""
import os

# R2 + botocore>=1.36 send checksum headers by default that can break uploads;
# only send them when an operation requires it.
os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")

import aioboto3

from .config import settings


def is_configured() -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket
    )


def _endpoint() -> str:
    return f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"


def _client():
    session = aioboto3.Session()
    return session.client(
        "s3",
        endpoint_url=_endpoint(),
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


async def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    async with _client() as s3:
        await s3.put_object(Bucket=settings.r2_bucket, Key=key, Body=data, ContentType=content_type)
    return key


async def upload_file(key: str, path: str, content_type: str | None = None) -> str:
    extra = {"ContentType": content_type} if content_type else None
    async with _client() as s3:
        await s3.upload_file(path, settings.r2_bucket, key, ExtraArgs=extra)
    return key


async def download_to(key: str, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with _client() as s3:
        await s3.download_file(settings.r2_bucket, key, path)
    return path


async def download_bytes(key: str) -> bytes:
    async with _client() as s3:
        obj = await s3.get_object(Bucket=settings.r2_bucket, Key=key)
        return await obj["Body"].read()


async def delete(key: str) -> None:
    async with _client() as s3:
        await s3.delete_object(Bucket=settings.r2_bucket, Key=key)


async def signed_url(key: str, expires: int = 3600) -> str:
    """Presigned GET URL so the browser can fetch a private object directly."""
    async with _client() as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket, "Key": key},
            ExpiresIn=expires,
        )


async def ensure_lifecycle(days: int = 2, prefix: str = "") -> None:
    """Set the bucket to auto-delete objects after `days` (48h = 2). Idempotent.
    Requires bucket-config permission; if the token is object-scoped this raises
    and the rule should be set once in the R2 dashboard instead."""
    config = {
        "Rules": [{
            "ID": f"expire-{days}d",
            "Status": "Enabled",
            "Filter": {"Prefix": prefix},
            "Expiration": {"Days": days},
        }]
    }
    async with _client() as s3:
        await s3.put_bucket_lifecycle_configuration(
            Bucket=settings.r2_bucket, LifecycleConfiguration=config
        )
