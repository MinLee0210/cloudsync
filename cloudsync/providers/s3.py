from typing import Dict, Optional
import boto3
from botocore.client import Config

from .base import CloudProvider, RemoteFile


class S3Provider(CloudProvider):
    """Works with AWS S3, MinIO, or any S3-compatible endpoint."""

    def __init__(
        self,
        bucket: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
        session_token: Optional[str] = None,
        profile: Optional[str] = None,
        verify: Optional[bool] = None,
    ):
        self.bucket = bucket
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.endpoint_url = endpoint_url
        self.region = region
        self.client = session.client(
            "s3",
            endpoint_url=endpoint_url,  # None -> AWS; set for MinIO e.g. http://localhost:9000
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
            verify=verify,
            config=Config(signature_version="s3v4"),
        )

    def identity(self) -> str:
        endpoint = self.endpoint_url or "aws"
        return f"s3:{endpoint}:{self.region}:{self.bucket}"

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
                etag = obj.get("ETag", "").strip('"')
                result[rel_path] = RemoteFile(
                    id=obj["Key"],
                    path=rel_path,
                    size=obj["Size"],
                    mtime=obj["LastModified"].isoformat(),
                    # Multipart ETags contain a dash and are not content MD5 values.
                    hash=etag if "-" not in etag else None,
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
