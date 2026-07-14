<div class="hero" markdown>

# cloudsync

### A quiet, predictable bridge from a local folder to cloud storage.

`cloudsync` mirrors a local directory to Google Drive, Amazon S3, or an S3-compatible service such as MinIO. It keeps a small local SQLite ledger so repeat runs can skip unchanged files and makes remote cleanup explicit.

<div class="hero-actions">

[Install cloudsync](guides/installation.md){ .md-button .md-button--primary }
[Read the sync model](guides/sync-model.md){ .md-button }

</div>
</div>

## The short version

```bash
cloudsync sync ./archive \
  --provider s3 \
  --bucket my-bucket \
  --access-key "$AWS_ACCESS_KEY_ID" \
  --secret-key "$AWS_SECRET_ACCESS_KEY" \
  --remote-root workstation
```

The default is a one-way sync: local files are uploaded or updated, unchanged files are skipped, and files removed locally are deleted remotely. Use `--no-delete` when you want an upload/update pass without remote cleanup.

## What it supports

<div class="feature-grid" markdown>

<div class="feature-card" markdown>

#### Local-first

The local directory is the source of truth. A SQLite state file records remote IDs and content hashes between runs.

</div>

<div class="feature-card" markdown>

#### Provider-ready

Google Drive, S3, and MinIO share one small provider interface. Remote paths stay portable across backends.

</div>

<div class="feature-card" markdown>

#### Inspectable

Quota checks return plain dictionaries, and `SyncResult` reports uploaded, updated, deleted, and skipped paths.

</div>

</div>

!!! warning "Deletion is intentional"
    Sync deletion is enabled by default. Start with `--no-delete` for a dry operational rollout, and make sure the local path exists before enabling cleanup.

## Choose a path

- New to the project? Start with [Installation](guides/installation.md).
- Setting up a backend? See [Google Drive](guides/google-drive.md) or [S3 and MinIO](guides/s3-minio.md).
- Automating it? Use the [CLI reference](reference/cli.md) or [Python API](reference/python-api.md).
