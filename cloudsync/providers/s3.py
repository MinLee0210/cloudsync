from typing import Dict, Optional
import boto3
from botocore.client import Config

from .base import CloudProvider, RemoteFile


class S3Provider(CloudProvider):
    """Works with AWS S3, MinIO, or any S3-compatible endpoint."""

    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,  # None -> AWS; set for MinIO e.g. http://localhost:9000
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    # ------------------------------------------------------------------
    def list_files(self, remote_path: str = "") -> Dict[str, RemoteFile]:
        prefix = remote_path.strip("/")
        if prefix:
            prefix += "/"

        result: Dict[str, RemoteFile] = {}
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                rel_path = obj["Key"][len(prefix) :]
                if not rel_path:
                    continue
                result[rel_path] = RemoteFile(
                    id=obj["Key"],
                    path=rel_path,
                    size=obj["Size"],
                    mtime=obj["LastModified"].isoformat(),
                    hash=obj.get("ETag", "").strip('"'),
                )
        return result

    # ------------------------------------------------------------------
    def upload(self, local_path: str, remote_path: str) -> str:
        key = remote_path.strip("/")
        self.client.upload_file(local_path, self.bucket, key)
        return key

    def update(self, remote_id: str, local_path: str) -> None:
        # S3 has no in-place update; re-upload overwrites the object.
        self.client.upload_file(local_path, self.bucket, remote_id)

    def delete(self, remote_id: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=remote_id)

    # ------------------------------------------------------------------
    def get_storage_info(self) -> dict:
        """S3/MinIO buckets have no built-in quota API; report usage only."""
        usage = 0
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket):
            for obj in page.get("Contents", []):
                usage += obj["Size"]
        return {"usage": usage, "limit": None, "available": None}
