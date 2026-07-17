import sqlite3

import pytest

from cloudsync.scanner import ScanError, scan_dir
from cloudsync.state import SCHEMA_VERSION, SyncState
from cloudsync.sync import SyncSafetyError, check_quota, sync
from tests.fake_provider import FakeProvider


@pytest.fixture
def state(tmp_path):
    with SyncState(tmp_path / "state.db") as value:
        yield value


def test_upload_skip_update_and_reconcile_remote(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    (local / "hello.txt").write_text("one")
    provider = FakeProvider()

    assert sync(str(local), provider, state=state).uploaded == ["hello.txt"]
    assert sync(str(local), provider, state=state).skipped == ["hello.txt"]
    (local / "hello.txt").write_text("two")
    assert sync(str(local), provider, state=state).updated == ["hello.txt"]
    provider.files["hello.txt"] = b"remote edit"
    assert sync(str(local), provider, state=state).updated == ["hello.txt"]


def test_delete_is_opt_in_and_only_managed_files(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    file = local / "managed.txt"
    file.write_text("data")
    provider = FakeProvider()
    sync(str(local), provider, state=state)
    provider.files["unmanaged.txt"] = b"keep"
    file.unlink()

    result = sync(str(local), provider, state=state)
    assert result.deleted == []
    assert set(provider.files) == {"managed.txt", "unmanaged.txt"}
    result = sync(str(local), provider, state=state, delete_remote=True, max_delete_percent=100)
    assert result.deleted == ["managed.txt"]
    assert provider.files == {"unmanaged.txt": b"keep"}


def test_rename_uploads_new_path_and_optionally_deletes_old(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    old = local / "old.txt"
    old.write_text("same content")
    provider = FakeProvider()
    sync(str(local), provider, state=state)
    old.rename(local / "new.txt")

    result = sync(str(local), provider, state=state, delete_remote=True, max_delete_percent=100)
    assert result.uploaded == ["new.txt"]
    assert result.deleted == ["old.txt"]
    assert provider.files == {"new.txt": b"same content"}


def test_dry_run_mutates_nothing(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    (local / "file").write_text("data")
    provider = FakeProvider()
    result = sync(str(local), provider, state=state, dry_run=True)
    assert result.uploaded == ["file"]
    assert provider.files == {}
    job = state.ensure_job(str(local), provider.identity(), "")
    assert state.get_all(job.id) == {}


def test_jobs_are_isolated(tmp_path, state):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "same").write_text("first")
    (second / "same").write_text("second")
    a, b = FakeProvider("a"), FakeProvider("b")
    sync(str(first), a, state=state)
    sync(str(second), b, state=state)
    assert a.files["same"] == b"first"
    assert b.files["same"] == b"second"
    assert len(state.conn.execute("SELECT id FROM sync_jobs").fetchall()) == 2


def test_deletion_guard(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    provider = FakeProvider()
    for index in range(2):
        (local / str(index)).write_text("x")
    sync(str(local), provider, state=state)
    for path in local.iterdir():
        path.unlink()
    with pytest.raises(SyncSafetyError):
        sync(str(local), provider, state=state, delete_remote=True)


def test_failure_is_recorded_and_retriable(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    (local / "file").write_text("x")
    provider = FakeProvider()
    provider.fail_on = "upload"
    with pytest.raises(RuntimeError):
        sync(str(local), provider, state=state)
    assert state.conn.execute("SELECT status FROM sync_runs").fetchone()[0] == "failed"
    provider.fail_on = None
    assert sync(str(local), provider, state=state).uploaded == ["file"]


def test_missing_root_and_state_file_exclusion(tmp_path, state):
    with pytest.raises(ScanError):
        scan_dir(tmp_path / "missing")
    local = tmp_path / "local"
    local.mkdir()
    nested_state = local / "state.db"
    with SyncState(nested_state):
        files = scan_dir(str(local), state_path=str(nested_state))
    assert files == {}


def test_paths_and_excludes(tmp_path):
    local = tmp_path / "local"
    local.mkdir()
    (local / "it's fine ☃.txt").write_text("yes")
    (local / "ignored.tmp").write_text("no")
    assert list(scan_dir(str(local), exclude=["*.tmp"])) == ["it's fine ☃.txt"]


def test_quota_uses_upload_delta_and_unknown_is_not_true(tmp_path, state):
    local = tmp_path / "local"
    local.mkdir()
    (local / "f").write_text("123")
    provider = FakeProvider()
    assert check_quota(str(local), provider, state=state)["upload_size"] == 3
    sync(str(local), provider, state=state)
    assert check_quota(str(local), provider, state=state)["upload_size"] == 0
    provider.get_storage_info = lambda: {"usage": 3, "limit": None, "available": None}
    assert check_quota(str(local), provider, state=state)["fits"] is None


def test_legacy_schema_migrates(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE sync_state(path TEXT PRIMARY KEY, remote_id TEXT NOT NULL, hash TEXT, size INTEGER, mtime REAL)"
    )
    connection.commit()
    connection.close()
    with SyncState(path) as state:
        assert state.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert state.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='legacy_sync_state'"
        ).fetchone()
