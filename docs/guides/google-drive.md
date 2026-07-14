# Google Drive

## One-time setup

1. Create an OAuth client for a Desktop app in Google Cloud Console.
2. Enable the Google Drive API.
3. Download the client file as `credentials.json`.
4. Run a sync. A browser window opens for consent and cloudsync caches the token in `token.json`.

```bash
cloudsync sync ./archive --provider gdrive --remote-root backups
```

The default Drive parent is the account root. To sync below a specific folder, pass its ID:

```bash
cloudsync sync ./archive \
  --provider gdrive \
  --root-folder-id YOUR_FOLDER_ID \
  --remote-root backups
```

## Folder behavior

Missing folders in the upload path are created as needed. Listing a remote path is read-only: asking cloudsync to inspect a missing Drive folder returns no files and does not create it.

## Quota

```bash
cloudsync quota ./archive --provider gdrive
```

The command reports local size, current Drive usage, quota limit, available space, and whether the local directory fits.
