import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

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
    workers: int = 1,
    ignore_patterns: Optional[List[str]] = None,
) -> SyncResult:
    """
    One-way sync: local_dir -> provider/remote_root.

    - New/changed local files are uploaded.
    - Files removed locally are deleted remotely (if delete_remote=True).
    - Can execute concurrently with workers > 1.
    """
    own_state = state is None
    if own_state:
        state = SyncState()

    state_lock = threading.Lock()

    def do_upload(rel_path, lf, remote_path):
        remote_id = provider.upload(lf.path, remote_path)
        with state_lock:
            state.set(rel_path, remote_id, lf.hash, lf.size, lf.mtime)

    def do_update(rel_path, lf, record):
        provider.update(record.remote_id, lf.path)
        with state_lock:
            state.set(rel_path, record.remote_id, lf.hash, lf.size, lf.mtime)

    def do_delete(rel_path, record):
        provider.delete(record.remote_id)
        with state_lock:
            state.delete(rel_path)

    try:
        result = SyncResult()
        # Scan completely before changing the provider. A scan error must not
        # be interpreted as an empty local directory.
        local_files = scan_dir(local_dir, ignore_patterns=ignore_patterns)
        known = state.get_all()

        upload_tasks = []
        update_tasks = []
        skipped_files = []

        # Upload new / changed files
        for rel_path, lf in local_files.items():
            record = known.get(rel_path)
            remote_path = f"{remote_root}/{rel_path}" if remote_root else rel_path

            if record is None:
                upload_tasks.append((rel_path, lf, remote_path))
            elif record.hash != lf.hash:
                update_tasks.append((rel_path, lf, record))
            else:
                skipped_files.append(rel_path)

        result.skipped = skipped_files

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures_to_path = {}
                for rel_path, lf, remote_path in upload_tasks:
                    f = executor.submit(do_upload, rel_path, lf, remote_path)
                    futures_to_path[f] = (rel_path, "upload")
                for rel_path, lf, record in update_tasks:
                    f = executor.submit(do_update, rel_path, lf, record)
                    futures_to_path[f] = (rel_path, "update")

                for f in as_completed(futures_to_path):
                    rel_path, task_type = futures_to_path[f]
                    try:
                        f.result()
                        if task_type == "upload":
                            result.uploaded.append(rel_path)
                        else:
                            result.updated.append(rel_path)
                    except Exception as exc:
                        logger.error(f"Failed to {task_type} {rel_path}: {exc}")
                        raise
        else:
            for rel_path, lf, remote_path in upload_tasks:
                do_upload(rel_path, lf, remote_path)
                result.uploaded.append(rel_path)
            for rel_path, lf, record in update_tasks:
                do_update(rel_path, lf, record)
                result.updated.append(rel_path)

        # Delete files that no longer exist locally
        if delete_remote:
            delete_tasks = []
            for rel_path, record in known.items():
                if rel_path not in local_files:
                    delete_tasks.append((rel_path, record))

            if delete_tasks:
                if workers > 1:
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        futures_to_path = {}
                        for rel_path, record in delete_tasks:
                            f = executor.submit(do_delete, rel_path, record)
                            futures_to_path[f] = rel_path

                        for f in as_completed(futures_to_path):
                            rel_path = futures_to_path[f]
                            try:
                                f.result()
                                result.deleted.append(rel_path)
                            except Exception as exc:
                                logger.error(f"Failed to delete {rel_path}: {exc}")
                                raise
                else:
                    for rel_path, record in delete_tasks:
                        do_delete(rel_path, record)
                        result.deleted.append(rel_path)

        return result
    finally:
        if own_state:
            state.close()


def check_quota(
    local_dir: str,
    provider: CloudProvider,
    ignore_patterns: Optional[List[str]] = None,
) -> dict:
    """Compare local directory size against remote available storage."""
    from .scanner import get_dir_size

    local_size = get_dir_size(local_dir, ignore_patterns=ignore_patterns)
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
