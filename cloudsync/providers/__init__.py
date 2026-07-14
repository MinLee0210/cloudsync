from importlib import import_module

from .base import CloudProvider, RemoteFile

# Keep SDK imports lazy. Importing core scanning/state utilities should not
# require every provider's optional SDK.
PROVIDERS = {
    "gdrive": "cloudsync.providers.gdrive:GoogleDriveProvider",
    "s3": "cloudsync.providers.s3:S3Provider",
    "minio": "cloudsync.providers.s3:S3Provider",  # alias
}


def __getattr__(name):
    if name == "GoogleDriveProvider":
        return import_module(".gdrive", __name__).GoogleDriveProvider
    if name == "S3Provider":
        return import_module(".s3", __name__).S3Provider
    raise AttributeError(name)

__all__ = [
    "CloudProvider",
    "RemoteFile",
    "GoogleDriveProvider",
    "S3Provider",
    "PROVIDERS",
]
