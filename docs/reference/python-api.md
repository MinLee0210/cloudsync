# Python API

## `sync`

```python
from cloudsync import S3Provider, sync

provider = S3Provider(
    bucket="my-bucket",
    access_key="...",
    secret_key="...",
)
result = sync("./archive", provider, remote_root="backups", delete_remote=False)
print(result.uploaded, result.updated, result.skipped)
```

`sync(local_dir, provider, remote_root="", state=None, delete_remote=True)` returns a `SyncResult` with four lists: `uploaded`, `updated`, `deleted`, and `skipped`.

## `check_quota`

```python
from cloudsync import check_quota

info = check_quota("./archive", provider)
```

The result contains `local_size`, `remote_usage`, `remote_limit`, `remote_available`, and `fits`.

## Scanning

```python
from cloudsync import get_dir_size, scan_dir

files = scan_dir("./archive")
total_bytes = get_dir_size("./archive")
```

Scanning a missing path raises `FileNotFoundError`.
