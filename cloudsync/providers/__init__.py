from .base import CloudProvider, RemoteFile
from .gdrive import GoogleDriveProvider
from .s3 import S3Provider

PROVIDERS = {
    "gdrive": GoogleDriveProvider,
    "s3": S3Provider,
    "minio": S3Provider,  # alias - configure with endpoint_url
}

__all__ = [
    "CloudProvider",
    "RemoteFile",
    "GoogleDriveProvider",
    "S3Provider",
    "PROVIDERS",
]
