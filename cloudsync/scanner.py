from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class LocalFile:
    path: str
    size: int
    mtime: float
    hash: str


class ScanError(RuntimeError):
    pass


def _md5(path: str, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_dir(
    root: str,
    *,
    exclude: Iterable[str] = (),
    state_path: Optional[str] = None,
    follow_symlinks: bool = False,
) -> Dict[str, LocalFile]:
    """Return a stable mapping of POSIX-style relative paths to local files."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise ScanError(f"Local root does not exist: {root_path}")
    if not root_path.is_dir():
        raise ScanError(f"Local root is not a directory: {root_path}")
    if not os.access(root_path, os.R_OK | os.X_OK):
        raise ScanError(f"Local root is not readable: {root_path}")
    ignored_state = str(Path(state_path).resolve()) if state_path else None
    result: Dict[str, LocalFile] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=follow_symlinks):
            dirnames.sort()
            filenames.sort()
            for name in filenames:
                absolute = os.path.join(dirpath, name)
                relative = os.path.relpath(absolute, root_path).replace(os.sep, "/")
                if any(fnmatch.fnmatch(relative, pattern) for pattern in exclude):
                    continue
                resolved = str(Path(absolute).resolve())
                state_files = {
                    ignored_state,
                    f"{ignored_state}-wal",
                    f"{ignored_state}-shm",
                    f"{ignored_state}-journal",
                }
                if ignored_state and resolved in state_files:
                    continue
                if os.path.islink(absolute) and not follow_symlinks:
                    continue
                before = os.stat(absolute, follow_symlinks=follow_symlinks)
                if not os.path.isfile(absolute):
                    continue
                content_hash = _md5(absolute)
                after = os.stat(absolute, follow_symlinks=follow_symlinks)
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ScanError(f"File changed while scanning: {absolute}")
                result[relative] = LocalFile(absolute, after.st_size, after.st_mtime, content_hash)
    except OSError as exc:
        raise ScanError(f"Could not scan {root_path}: {exc}") from exc
    return result


def get_dir_size(root: str, **kwargs) -> int:
    return sum(file.size for file in scan_dir(root, **kwargs).values())
