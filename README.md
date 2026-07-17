# cloudsync

Safely synchronize a local directory to Google Drive, AWS S3, or MinIO. The
engine previews changes by reconciling local files, remote files, and isolated
SQLite state. Remote deletion is disabled unless explicitly requested.

> cloudsync is alpha software. Always inspect a plan before enabling deletion.

## Installation

```bash
pip install 'cloudsync[gdrive]'  # Google Drive
pip install 'cloudsync[s3]'      # AWS S3 or MinIO
```

For development, run `uv sync --all-extras`.

## Safe workflow

```bash
cloudsync plan ./photos --provider s3 --bucket backups --remote-root photos --json
cloudsync sync ./photos --provider s3 --bucket backups --remote-root photos --dry-run
cloudsync sync ./photos --provider s3 --bucket backups --remote-root photos
```

Deletion is opt-in and only applies to previously managed files:

```bash
cloudsync plan ./photos --provider s3 --bucket backups --remote-root photos --delete
cloudsync sync ./photos --provider s3 --bucket backups --remote-root photos --delete
```

By default a run is rejected if it would delete more than 100 files or 25% of
planned entries. Override those guards deliberately with `--max-delete` and
`--max-delete-percent`.

State defaults to `$XDG_STATE_HOME/cloudsync/state.db` (or
`~/.local/state/cloudsync/state.db`) and is isolated by canonical local root,
provider destination, and remote root. Use `--db` to choose another location.

## Credentials

For S3, cloudsync uses boto3's normal credential chain, including environment
variables, shared profiles, and IAM/workload roles:

```bash
cloudsync plan ./data --provider s3 --bucket my-bucket --profile production
cloudsync plan ./data --provider minio --bucket my-bucket \
  --endpoint-url http://localhost:9000
```

Avoid putting secrets directly in command history. Legacy secret flags remain
hidden for compatibility.

For Google Drive, create Desktop OAuth credentials and provide the downloaded
file using `--credentials`. The refreshed token is stored with owner-only file
permissions.

## Python API

```python
from cloudsync import S3Provider, SyncState, create_plan, apply_plan

provider = S3Provider(bucket="my-bucket", profile="production")
with SyncState("state.db") as state:
    plan = create_plan("./data", provider, remote_root="backup", state=state)
    print(plan.to_dict())
    result = apply_plan(plan, provider, state, remote_root="backup")
```

## Current behavior and recovery

- Local content is authoritative for managed paths.
- Unmanaged remote files are left untouched.
- A missing managed remote file is uploaded again.
- A remotely modified managed file is overwritten by the local copy.
- A rename is an upload of the new path; with `--delete`, the previously managed
  old path is then deleted.
- Failed runs are recorded and can be retried; successful operations already
  visible remotely are reconciled on the next plan.
- Symlinks are skipped, unreadable/incomplete scans abort before mutation, and a
  file changing during hashing aborts the scan.
- S3-compatible storage generally cannot report a quota; `fits` is then `null`.

Use repeatable `--exclude` glob options for files that should not be synced.
See [TODO.md](TODO.md) for remaining limitations and planned work.
