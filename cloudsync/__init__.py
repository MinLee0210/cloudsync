from typing import TYPE_CHECKING

from .sync import SyncPlan, SyncResult, apply_plan, check_quota, create_plan, sync
from .state import SyncState
from .scanner import scan_dir, get_dir_size
from .providers import CloudProvider, PROVIDERS

if TYPE_CHECKING:
    from .providers.gdrive import GoogleDriveProvider
    from .providers.s3 import S3Provider


def __getattr__(name):
    if name in {"GoogleDriveProvider", "S3Provider"}:
        from . import providers

        return getattr(providers, name)
    raise AttributeError(name)


__all__ = [
    "sync",
    "check_quota",
    "SyncResult",
    "SyncPlan",
    "create_plan",
    "apply_plan",
    "SyncState",
    "scan_dir",
    "get_dir_size",
    "CloudProvider",
    "GoogleDriveProvider",
    "S3Provider",
    "PROVIDERS",
]
