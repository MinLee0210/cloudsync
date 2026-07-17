from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable, List, Optional

from .providers.base import CloudProvider, RemoteFile
from .scanner import LocalFile, scan_dir
from .state import SyncState

logger = logging.getLogger(__name__)


class SyncSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncOperation:
    action: str
    path: str
    reason: str
    local: Optional[LocalFile] = None
    remote: Optional[RemoteFile] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.local:
            data["local"]["path"] = self.path
        return data


@dataclass
class SyncPlan:
    job_id: str
    operations: List[SyncOperation] = field(default_factory=list)

    @property
    def deletions(self) -> List[SyncOperation]:
        return [op for op in self.operations if op.action == "delete"]

    @property
    def changes(self) -> List[SyncOperation]:
        return [op for op in self.operations if op.action != "skip"]

    @property
    def upload_bytes(self) -> int:
        return sum(
            op.local.size for op in self.changes if op.local and op.action in {"upload", "update"}
        )

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "upload_bytes": self.upload_bytes,
            "operations": [op.to_dict() for op in self.operations],
        }


@dataclass
class SyncResult:
    uploaded: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"SyncResult(uploaded={len(self.uploaded)}, updated={len(self.updated)}, "
            f"deleted={len(self.deleted)}, skipped={len(self.skipped)}, errors={len(self.errors)})"
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def _remote_path(remote_root: str, relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise SyncSafetyError(f"Unsafe remote path: {relative!r}")
    root = remote_root.strip("/")
    return f"{root}/{relative}" if root else relative


def create_plan(
    local_dir: str,
    provider: CloudProvider,
    *,
    remote_root: str = "",
    state: SyncState,
    delete_remote: bool = False,
    exclude: Iterable[str] = (),
) -> SyncPlan:
    """Reconcile local, remote, and stored snapshots without mutating them."""
    job = state.ensure_job(local_dir, provider.identity(), remote_root)
    local_files = scan_dir(local_dir, exclude=exclude, state_path=state.db_path)
    remote_files = provider.list_files(remote_root)
    known = state.get_all(job.id)
    operations: List[SyncOperation] = []

    for path, local in local_files.items():
        remote = remote_files.get(path)
        record = known.get(path)
        _remote_path(remote_root, path)
        if remote is None:
            operations.append(SyncOperation("upload", path, "missing remotely", local=local))
        elif remote.hash and remote.hash == local.hash:
            operations.append(SyncOperation("skip", path, "content matches", local, remote))
        elif record and record.hash == local.hash and record.remote_id == remote.id:
            operations.append(SyncOperation("update", path, "remote changed", local, remote))
        else:
            operations.append(SyncOperation("update", path, "local content differs", local, remote))

    for path, record in known.items():
        if path in local_files:
            continue
        remote = remote_files.get(path)
        if remote is None:
            continue
        if delete_remote:
            operations.append(
                SyncOperation("delete", path, "managed local file removed", remote=remote)
            )
        else:
            operations.append(SyncOperation("skip", path, "deletion disabled", remote=remote))
    return SyncPlan(job.id, operations)


def apply_plan(
    plan: SyncPlan,
    provider: CloudProvider,
    state: SyncState,
    *,
    remote_root: str = "",
    dry_run: bool = False,
    max_delete: int = 100,
    max_delete_percent: float = 25.0,
) -> SyncResult:
    result = SyncResult()
    deletions = len(plan.deletions)
    managed = max(len(plan.operations), 1)
    if deletions > max_delete or deletions / managed * 100 > max_delete_percent:
        raise SyncSafetyError(
            f"Refusing {deletions} deletions: safety limit is {max_delete} files and {max_delete_percent:g}%"
        )
    if dry_run:
        result_lists = {
            "upload": result.uploaded,
            "update": result.updated,
            "delete": result.deleted,
            "skip": result.skipped,
        }
        for op in plan.operations:
            result_lists[op.action].append(op.path)
        return result

    run_id = state.begin_run(plan.job_id)
    try:
        for op in plan.operations:
            if op.action == "upload":
                if op.local is None:
                    raise RuntimeError(f"Upload operation has no local file: {op.path}")
                remote_id = provider.upload(op.local.path, _remote_path(remote_root, op.path))
                state.set(
                    op.path, remote_id, op.local.hash, op.local.size, op.local.mtime, plan.job_id
                )
                result.uploaded.append(op.path)
            elif op.action == "update":
                if op.local is None or op.remote is None:
                    raise RuntimeError(f"Update operation is incomplete: {op.path}")
                provider.update(op.remote.id, op.local.path)
                state.set(
                    op.path, op.remote.id, op.local.hash, op.local.size, op.local.mtime, plan.job_id
                )
                result.updated.append(op.path)
            elif op.action == "delete":
                if op.remote is None:
                    raise RuntimeError(f"Delete operation has no remote file: {op.path}")
                provider.delete(op.remote.id)
                state.delete(op.path, plan.job_id)
                result.deleted.append(op.path)
            else:
                if op.local and op.remote:
                    state.set(
                        op.path,
                        op.remote.id,
                        op.local.hash,
                        op.local.size,
                        op.local.mtime,
                        plan.job_id,
                    )
                result.skipped.append(op.path)
            state.commit()
    except Exception as exc:
        state.rollback()
        state.finish_run(run_id, "failed", str(exc))
        raise
    state.finish_run(run_id, "completed")
    return result


def sync(
    local_dir: str,
    provider: CloudProvider,
    remote_root: str = "",
    state: Optional[SyncState] = None,
    delete_remote: bool = False,
    *,
    dry_run: bool = False,
    exclude: Iterable[str] = (),
    max_delete: int = 100,
    max_delete_percent: float = 25.0,
) -> SyncResult:
    own_state = state is None
    if state is None:
        state = SyncState(default_state_path())
    try:
        plan = create_plan(
            local_dir,
            provider,
            remote_root=remote_root,
            state=state,
            delete_remote=delete_remote,
            exclude=exclude,
        )
        return apply_plan(
            plan,
            provider,
            state,
            remote_root=remote_root,
            dry_run=dry_run,
            max_delete=max_delete,
            max_delete_percent=max_delete_percent,
        )
    finally:
        if own_state:
            state.close()


def default_state_path() -> str:
    import os

    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return str(base / "cloudsync" / "state.db")


def check_quota(
    local_dir: str,
    provider: CloudProvider,
    *,
    remote_root: str = "",
    state: Optional[SyncState] = None,
) -> dict:
    own_state = state is None
    if state is None:
        state = SyncState(default_state_path())
    try:
        plan = create_plan(local_dir, provider, remote_root=remote_root, state=state)
        storage = provider.get_storage_info()
        available = storage.get("available")
        required = plan.upload_bytes
        fits = None if available is None else required <= available
        return {
            "upload_size": required,
            "remote_usage": storage["usage"],
            "remote_limit": storage["limit"],
            "remote_available": available,
            "fits": fits,
        }
    finally:
        if own_state:
            state.close()
