import hashlib
import os
from typing import Dict, NamedTuple


class LocalFile(NamedTuple):
    path: str  # absolute path
    size: int
    mtime: float
    hash: str  # md5


def _md5(path: str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dir(root: str) -> Dict[str, LocalFile]:
    """Return mapping of relative path (posix-style) -> LocalFile."""
    result: Dict[str, LocalFile] = {}
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            abs_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(abs_path, root).replace(os.sep, "/")
            stat = os.stat(abs_path)
            result[rel_path] = LocalFile(
                path=abs_path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                hash=_md5(abs_path),
            )
    return result


def get_dir_size(root: str) -> int:
    """Total size in bytes of all files under root."""
    return sum(f.size for f in scan_dir(root).values())
