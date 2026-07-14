import fnmatch
import hashlib
import os
from typing import Dict, List, NamedTuple, Optional


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


def parse_ignore_patterns(
    root: str, additional_patterns: Optional[List[str]] = None
) -> List[str]:
    patterns = []
    ignore_file = os.path.join(root, ".cloudsyncignore")
    if os.path.isfile(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    if additional_patterns:
        for pat in additional_patterns:
            pat = pat.strip()
            if pat and not pat.startswith("#"):
                patterns.append(pat)
    return patterns


def should_ignore(rel_path: str, patterns: List[str]) -> bool:
    parts = rel_path.split("/")
    for pattern in patterns:
        pat = pattern.rstrip("/")
        if "/" not in pat:
            if any(fnmatch.fnmatch(part, pat) for part in parts):
                return True
        else:
            if pat.startswith("/"):
                pat_match = pat[1:]
            else:
                pat_match = pat
            if fnmatch.fnmatch(rel_path, pat_match):
                return True
            prefix_matched = False
            for i in range(1, len(parts)):
                prefix = "/".join(parts[:i])
                if fnmatch.fnmatch(prefix, pat_match):
                    prefix_matched = True
                    break
            if prefix_matched:
                return True
    return False


def scan_dir(
    root: str, ignore_patterns: Optional[List[str]] = None
) -> Dict[str, LocalFile]:
    """Return mapping of relative path (posix-style) -> LocalFile."""
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Local directory does not exist: {root}")

    patterns = parse_ignore_patterns(root, ignore_patterns)
    result: Dict[str, LocalFile] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter dirnames in-place to avoid entering ignored directories
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir_prefix = ""
        else:
            rel_dir_prefix = rel_dir.replace(os.sep, "/") + "/"

        for d in list(dirnames):
            rel_d_path = rel_dir_prefix + d
            if should_ignore(rel_d_path, patterns):
                dirnames.remove(d)

        for name in filenames:
            abs_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(abs_path, root).replace(os.sep, "/")
            if should_ignore(rel_path, patterns):
                continue
            stat = os.stat(abs_path)
            result[rel_path] = LocalFile(
                path=abs_path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                hash=_md5(abs_path),
            )
    return result


def get_dir_size(root: str, ignore_patterns: Optional[List[str]] = None) -> int:
    """Total size in bytes of all files under root."""
    return sum(f.size for f in scan_dir(root, ignore_patterns=ignore_patterns).values())
