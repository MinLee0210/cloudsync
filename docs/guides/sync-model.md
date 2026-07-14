# Sync model

`cloudsync` performs a one-way sync from a local directory to a remote prefix or folder.

```text
scan local files -> compare SQLite ledger -> upload/update -> optional remote deletes
```

## What happens on each run

1. The local directory is validated and scanned recursively.
2. Each file is hashed with MD5 and recorded with its size and modification time.
3. Files without a ledger entry are uploaded.
4. Files whose content hash changed are updated in place.
5. Files with the same hash are skipped.
6. Tracked files missing locally are deleted remotely unless deletion is disabled.

The scan completes before provider mutations begin. A missing local directory raises an error instead of looking like an empty directory.

## State database

The default state file is `.cloudsync_state.db`. It maps a relative local path to:

- the provider's remote ID;
- the last content hash;
- the last known size and modification time.

Use a separate `--db` path for each local directory and remote destination.

!!! tip
    Use `--no-delete` when testing credentials, changing remote roots, or introducing a new machine. Re-enable deletion only after reviewing the first run.

!!! note
    The ledger is not a full remote reconciliation database. If remote files are changed or removed outside cloudsync, the next run may not detect that drift before using the stored remote ID.
