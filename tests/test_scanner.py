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


def test_scan_dir_with_ignore_patterns(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "keep.txt").write_bytes(b"123")
    (root / "ignore.tmp").write_bytes(b"12345")

    # Nested ignored folder
    nested = root / "node_modules"
    nested.mkdir()
    (nested / "dep.js").write_bytes(b"const a = 1;")

    # Nested folder to keep, with ignored file inside
    src = root / "src"
    src.mkdir()
    (src / "app.js").write_bytes(b"console.log()")
    (src / "app.tmp").write_bytes(b"temp")

    # 1. Test explicit ignore patterns
    res = scan_dir(str(root), ignore_patterns=["*.tmp", "node_modules/"])
    assert "keep.txt" in res
    assert "src/app.js" in res
    assert "ignore.tmp" not in res
    assert "node_modules/dep.js" not in res
    assert "src/app.tmp" not in res

    # 2. Test reading from .cloudsyncignore
    (root / ".cloudsyncignore").write_text("*.tmp\nnode_modules/\n")
    res2 = scan_dir(str(root))
    assert "keep.txt" in res2
    assert "src/app.js" in res2
    assert "ignore.tmp" not in res2
    assert "node_modules/dep.js" not in res2
    assert "src/app.tmp" not in res2
