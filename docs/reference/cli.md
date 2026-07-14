# CLI reference

The command has two operations: `sync` and `quota`.

## Sync

```bash
cloudsync sync LOCAL_DIR --provider PROVIDER [OPTIONS]
```

Common options:

| Option | Default | Purpose |
| --- | --- | --- |
| `--provider` | required | `gdrive`, `s3`, or `minio` |
| `--remote-root` | empty | Remote folder or object prefix |
| `--db` | `.cloudsync_state.db` | SQLite ledger path |
| `--no-delete` | off | Keep remote files removed locally |

Google Drive options include `--credentials`, `--token`, and `--root-folder-id`. S3/MinIO options include `--bucket`, `--access-key`, `--secret-key`, and `--endpoint-url`.

## Quota

```bash
cloudsync quota LOCAL_DIR --provider PROVIDER [OPTIONS]
```

This checks the local directory size against provider storage information without changing remote files.
