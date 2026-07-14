import logging
from typing import Optional

from .providers.base import CloudProvider
from .scanner import scan_dir
from .state import SyncState

logger = logging.getLogger(__name__)


class SyncResult:
    def __init__(self):
        self.uploaded = []
        self.updated = []
        self.deleted = []
        self.skipped = []

    def __repr__(self):
        return (
            f"SyncResult(uploaded={len(self.uploaded)}, updated={len(self.updated)}, "
            f"deleted={len(self.deleted)}, skipped={len(self.skipped)})"
        )


def sync(
    local_dir: str,
    provider: CloudProvider,
    remote_root: str = "",
    state: Optional[SyncState] = None,
    delete_remote: bool = True,
) -> SyncResult:
    """
    One-way sync: local_dir -> provider/remote_root.

    - New/changed local files are uploaded.
    - Files removed locally are deleted remotely (if delete_remote=True).
    """
    own_state = state is None
    if own_state:
        state = SyncState()

    try:
        result = SyncResult()
        # Scan completely before changing the provider. A scan error must not
        # be interpreted as an empty local directory.
        local_files = scan_dir(local_dir)
        known = state.get_all()

        # Upload new / changed files
        for rel_path, lf in local_files.items():
            record = known.get(rel_path)
            remote_path = f"{remote_root}/{rel_path}" if remote_root else rel_path

            if record is None:
                remote_id = provider.upload(lf.path, remote_path)
                state.set(rel_path, remote_id, lf.hash, lf.size, lf.mtime)
                result.uploaded.append(rel_path)
            elif record.hash != lf.hash:
                provider.update(record.remote_id, lf.path)
                state.set(rel_path, record.remote_id, lf.hash, lf.size, lf.mtime)
                result.updated.append(rel_path)
            else:
                result.skipped.append(rel_path)

        # Delete files that no longer exist locally
        if delete_remote:
            for rel_path, record in known.items():
                if rel_path not in local_files:
                    provider.delete(record.remote_id)
                    state.delete(rel_path)
                    result.deleted.append(rel_path)

        return result
    finally:
        if own_state:
            state.close()


def check_quota(local_dir: str, provider: CloudProvider) -> dict:
    """Compare local directory size against remote available storage."""
    from .scanner import get_dir_size

    local_size = get_dir_size(local_dir)
    storage = provider.get_storage_info()
    available = storage.get("available")

    fits = available is None or local_size <= available
    return {
        "local_size": local_size,
        "remote_usage": storage["usage"],
        "remote_limit": storage["limit"],
        "remote_available": available,
        "fits": fits,
    }
