import threading
from typing import Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .base import CloudProvider, RemoteFile
from ..auth import get_credentials

FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDriveProvider(CloudProvider):
    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
        root_folder_id: str = "root",
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.root_folder_id = root_folder_id
        self._thread_local = threading.local()
        self._lock = threading.Lock()
        self.creds = get_credentials(credentials_file, token_file)

    @property
    def service(self):
        if not hasattr(self._thread_local, "service"):
            self._thread_local.service = build("drive", "v3", credentials=self.creds)
        return self._thread_local.service

    # ------------------------------------------------------------------
    def _ensure_folder(self, name: str, parent_id: str) -> str:
        """Get or create a folder named `name` under parent_id, return its id."""
        with self._lock:
            query = (
                f"name = '{name}' and mimeType = '{FOLDER_MIME}' "
                f"and '{parent_id}' in parents and trashed = false"
            )
            res = self.service.files().list(q=query, fields="files(id)").execute()
            files = res.get("files", [])
            if files:
                return files[0]["id"]

            metadata = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
            folder = self.service.files().create(body=metadata, fields="id").execute()
            return folder["id"]

    def _find_folder(self, name: str, parent_id: str) -> Optional[str]:
        """Find a folder without creating it."""
        query = (
            f"name = '{name}' and mimeType = '{FOLDER_MIME}' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        files = (
            self.service.files()
            .list(q=query, fields="files(id)")
            .execute()
            .get("files", [])
        )
        return files[0]["id"] if files else None

    def _resolve_parent(self, remote_path: str, create: bool = True) -> Optional[str]:
        """Walk a folder path, optionally creating missing components."""
        parent_id = self.root_folder_id
        parts = [p for p in remote_path.split("/") if p]
        for part in parts:
            parent_id = (
                self._ensure_folder(part, parent_id)
                if create
                else self._find_folder(part, parent_id)
            )
            if parent_id is None:
                return None
        return parent_id

    # ------------------------------------------------------------------
    def list_files(self, remote_path: str = "") -> Dict[str, RemoteFile]:
        """Recursively list all non-folder files under remote_path."""
        root_id = (
            self._resolve_parent(remote_path, create=False)
            if remote_path
            else self.root_folder_id
        )
        if root_id is None:
            return {}
        result: Dict[str, RemoteFile] = {}
        self._walk(root_id, "", result)
        return result

    def _walk(self, folder_id: str, prefix: str, result: Dict[str, RemoteFile]):
        page_token = None
        while True:
            res = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, md5Checksum)",
                    pageToken=page_token,
                )
                .execute()
            )

            for f in res.get("files", []):
                rel_path = f"{prefix}/{f['name']}" if prefix else f["name"]
                if f["mimeType"] == FOLDER_MIME:
                    self._walk(f["id"], rel_path, result)
                else:
                    result[rel_path] = RemoteFile(
                        id=f["id"],
                        path=rel_path,
                        size=int(f.get("size", 0)),
                        mtime=f.get("modifiedTime", ""),
                        hash=f.get("md5Checksum"),
                    )

            page_token = res.get("nextPageToken")
            if not page_token:
                break

    # ------------------------------------------------------------------
    def upload(self, local_path: str, remote_path: str) -> str:
        parts = remote_path.rsplit("/", 1)
        if len(parts) == 2:
            folder_path, filename = parts
            parent_id = self._resolve_parent(folder_path)
        else:
            filename = remote_path
            parent_id = self.root_folder_id

        metadata = {"name": filename, "parents": [parent_id]}
        media = MediaFileUpload(local_path, resumable=True)
        f = (
            self.service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        return f["id"]

    def update(self, remote_id: str, local_path: str) -> None:
        media = MediaFileUpload(local_path, resumable=True)
        self.service.files().update(fileId=remote_id, media_body=media).execute()

    def delete(self, remote_id: str) -> None:
        self.service.files().update(fileId=remote_id, body={"trashed": True}).execute()

    # ------------------------------------------------------------------
    def get_storage_info(self) -> dict:
        about = self.service.about().get(fields="storageQuota").execute()
        quota = about["storageQuota"]
        usage = int(quota.get("usage", 0))
        limit = int(quota["limit"]) if "limit" in quota else None
        available = (limit - usage) if limit is not None else None
        return {"usage": usage, "limit": limit, "available": available}
