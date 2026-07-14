# cloudsync

**A predictable, one-way sync from local directories to cloud storage.**

`cloudsync` mirrors a local directory to Google Drive, Amazon S3, or an S3-compatible service such as MinIO. It uses a small SQLite ledger to identify unchanged files, preserve remote IDs, and make repeat runs efficient.

[![Tests](https://img.shields.io/badge/tests-5%20passed-246b56)](tests/)
[![Python](https://img.shields.io/badge/python-3.9%2B-246b56)](pyproject.toml)

## Features

- Upload new files and update files whose content changed.
- Skip unchanged files using content hashes.
- Delete remote files removed locally, with an explicit `--no-delete` safeguard.
- Check local size against provider quota information.
- Support Google Drive, AWS S3, and MinIO through one provider interface.
- Expose both a command-line interface and a Python API.
- Fail safely when the local directory is missing instead of treating it as empty.

## Installation

Requires Python 3.9 or newer.

```bash
python -m pip install -e .
```

For development:

```bash
python -m pip install -e '.[dev]'
pytest -q
```

Build or preview the documentation site:

```bash
python -m pip install -e '.[docs]'
mkdocs serve
```

The documentation is also available in [`docs/`](docs/) and is configured for GitHub Pages at [minlee0210.github.io/cloudsync](https://minlee0210.github.io/cloudsync/).

## Quick start

### Google Drive

Create a Desktop OAuth client, enable the Google Drive API, and save the downloaded client configuration as `credentials.json`. The first run opens a browser for consent and caches the token in `token.json`.

```bash
cloudsync sync ./archive \
  --provider gdrive \
  --remote-root backups
```

Use `--root-folder-id` to sync below a specific Drive folder.

### Amazon S3

```bash
cloudsync sync ./archive \
  --provider s3 \
  --bucket my-bucket \
  --access-key "$AWS_ACCESS_KEY_ID" \
  --secret-key "$AWS_SECRET_ACCESS_KEY" \
  --remote-root backups
```

### MinIO

```bash
cloudsync sync ./archive \
  --provider minio \
  --bucket backups \
  --access-key minioadmin \
  --secret-key minioadmin \
  --endpoint-url http://localhost:9000
```

## Sync behavior

Each run follows this sequence:

1. Validate and recursively scan the local directory.
2. Compare file hashes with the local SQLite ledger.
3. Upload new files and update changed files.
4. Skip files with unchanged content.
5. Delete tracked remote files that no longer exist locally, unless deletion is disabled.

The default state database is `.cloudsync_state.db`. Use a separate `--db` path for each local directory and remote destination.

> **Warning:** Remote deletion is enabled by default. Use `--no-delete` during initial setup, credential testing, or migration work.

## CLI reference

```bash
# Sync a directory
cloudsync sync LOCAL_DIR --provider PROVIDER [OPTIONS]

# Check storage before syncing
cloudsync quota LOCAL_DIR --provider PROVIDER [OPTIONS]
```

Common options:

| Option | Default | Description |
| --- | --- | --- |
| `--provider` | required | `gdrive`, `s3`, or `minio` |
| `--remote-root` | empty | Remote folder or object prefix |
| `--db` | `.cloudsync_state.db` | SQLite ledger location |
| `--no-delete` | disabled | Prevent remote cleanup during sync |

Provider-specific options are documented in the [CLI reference](docs/reference/cli.md).

## Python API

```python
from cloudsync import S3Provider, sync

provider = S3Provider(
    bucket="my-bucket",
    access_key="...",
    secret_key="...",
)

result = sync(
    "./archive",
    provider,
    remote_root="backups",
    delete_remote=False,
)

print(result.uploaded)
print(result.updated)
print(result.skipped)
```

The main public functions are:

- `sync(...)`, returning a `SyncResult` with `uploaded`, `updated`, `deleted`, and `skipped` paths.
- `check_quota(...)`, returning local size, remote usage, quota, availability, and fit status.
- `scan_dir(...)` and `get_dir_size(...)` for local filesystem inspection.

## Extending cloudsync

Implement `cloudsync.providers.base.CloudProvider` and register the provider in `cloudsync.providers.PROVIDERS`.

The interface requires:

```python
list_files(remote_path="")
upload(local_path, remote_path)
update(remote_id, local_path)
delete(remote_id)
get_storage_info()
```

See the [provider guide](docs/reference/providers.md) for details.

## Project documentation

- [Installation](docs/guides/installation.md)
- [Sync model and safety](docs/guides/sync-model.md)
- [Google Drive](docs/guides/google-drive.md)
- [S3 and MinIO](docs/guides/s3-minio.md)
- [CLI reference](docs/reference/cli.md)
- [Python API reference](docs/reference/python-api.md)
- [Contributing](docs/contributing.md)

## License

No license file is currently included in this repository.
