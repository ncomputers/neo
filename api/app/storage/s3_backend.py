"""S3 storage backend using presigned URLs."""

from __future__ import annotations

import os
from typing import Tuple
from uuid import uuid4

import boto3
from fastapi import UploadFile


class S3Backend:
    """Generate presigned URLs for uploads and downloads."""

    def __init__(self, client: boto3.client | None = None) -> None:
        endpoint = os.getenv("S3_ENDPOINT")
        region = os.getenv("S3_REGION")
        access = os.getenv("S3_ACCESS_KEY")
        secret = os.getenv("S3_SECRET_KEY")
        self.bucket = os.getenv("S3_BUCKET", "")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
        )

    async def save(self, tenant: str, file: UploadFile) -> Tuple[str, str]:
        key = f"{tenant}/{uuid4().hex}_{file.filename}"
        params = {
            "Bucket": self.bucket,
            "Key": key,
            "CacheControl": "public, max-age=86400",
        }
        etag = file.headers.get("ETag") or file.headers.get("etag")
        if etag:
            params["Metadata"] = {"etag": etag}
        url = self.client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=3600,
        )
        return url, key

    def read(self, key: str) -> bytes:  # pragma: no cover - passthrough
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseCacheControl": "public, max-age=86400",
            },
            ExpiresIn=3600,
        )
