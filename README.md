# cloudsync

Sync a local directory to cloud storage (Google Drive, S3, MinIO), with quota checking.

Read the full documentation at [minlee0210.github.io/cloudsync](https://minlee0210.github.io/cloudsync/).

## Install

```bash
pip install -e .
```

## Google Drive setup

1. Create OAuth client credentials (Desktop app) in Google Cloud Console, download as `credentials.json`.
2. First run opens a browser for consent; token is cached in `token.json`.

## Usage (Python)

```python
from cloudsync import GoogleDriveProvider, sync, check_quota

provider = GoogleDriveProvider(
    credentials_file="credentials.json",
    root_folder_id="root",  # or a specific Drive folder ID
)

print(check_quota("/path/to/local/dir", provider))
print(sync("/path/to/local/dir", provider, remote_root="backup"))
```

```python
from cloudsync import S3Provider, sync

# Works for AWS S3 or MinIO
provider = S3Provider(
    bucket="my-bucket",
    access_key="...",
    secret_key="...",
    endpoint_url="http://localhost:9000",  # omit for AWS S3
)

print(sync("/path/to/local/dir", provider, remote_root="backup"))
```

## CLI

```bash
cloudsync sync /path/to/dir --provider gdrive --remote-root backup
cloudsync quota /path/to/dir --provider gdrive

cloudsync sync /path/to/dir --provider minio --bucket mybucket \
    --access-key KEY --secret-key SECRET --endpoint-url http://localhost:9000
```

## Adding a new provider

Implement `cloudsync.providers.base.CloudProvider`:
- `list_files`, `upload`, `update`, `delete`, `get_storage_info`

Register it in `cloudsync/providers/__init__.py`'s `PROVIDERS` dict.
