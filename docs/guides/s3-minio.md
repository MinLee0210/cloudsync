# S3 and MinIO

The S3 provider works with AWS S3 and compatible object stores.

## AWS S3

```bash
cloudsync sync ./archive \
  --provider s3 \
  --bucket my-bucket \
  --access-key "$AWS_ACCESS_KEY_ID" \
  --secret-key "$AWS_SECRET_ACCESS_KEY" \
  --remote-root backups
```

## MinIO

Pass the MinIO endpoint and select the `minio` provider alias:

```bash
cloudsync sync ./archive \
  --provider minio \
  --bucket backups \
  --access-key minioadmin \
  --secret-key minioadmin \
  --endpoint-url http://localhost:9000
```

The CLI validates `--bucket`, `--access-key`, and `--secret-key` before creating the S3 client.

## Quota behavior

S3-compatible buckets do not expose a universal quota API through the provider. `quota` reports the current object usage, with an unknown limit and available space.
