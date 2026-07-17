from typing import TYPE_CHECKING

from .base import CloudProvider, RemoteFile

if TYPE_CHECKING:
    from .gdrive import GoogleDriveProvider
    from .s3 import S3Provider

PROVIDERS = {"gdrive": "GoogleDriveProvider", "s3": "S3Provider", "minio": "S3Provider"}


def __getattr__(name):
    if name == "GoogleDriveProvider":
        from .gdrive import GoogleDriveProvider

        return GoogleDriveProvider
    if name == "S3Provider":
        from .s3 import S3Provider

        return S3Provider
    raise AttributeError(name)


__all__ = ["CloudProvider", "RemoteFile", "GoogleDriveProvider", "S3Provider", "PROVIDERS"]
