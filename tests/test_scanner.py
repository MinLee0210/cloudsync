import pytest

from cloudsync.scanner import get_dir_size, scan_dir


def test_scan_dir_rejects_missing_path(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="Local directory does not exist"):
        scan_dir(str(missing))


def test_get_dir_size_counts_nested_files(tmp_path):
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "one.txt").write_bytes(b"123")
    (nested / "two.txt").write_bytes(b"12345")

    assert get_dir_size(str(root)) == 8
