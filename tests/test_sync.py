import pytest

from cloudsync.state import SyncState
from cloudsync.sync import sync


class FakeProvider:
    def __init__(self):
        self.calls = []

    def upload(self, local_path, remote_path):
        self.calls.append(("upload", local_path, remote_path))
        return f"id:{remote_path}"

    def update(self, remote_id, local_path):
        self.calls.append(("update", remote_id, local_path))

    def delete(self, remote_id):
        self.calls.append(("delete", remote_id))


def test_missing_local_directory_does_not_delete_remote_state(tmp_path):
    db = tmp_path / "state.db"
    state = SyncState(str(db))
    state.set("important.txt", "remote-1", "hash", 10, 1.0)
    provider = FakeProvider()

    with pytest.raises(FileNotFoundError):
        sync(str(tmp_path / "missing"), provider, state=state)

    assert provider.calls == []
    assert state.get("important.txt").remote_id == "remote-1"
    state.close()


def test_sync_uploads_new_files_and_skips_unchanged_files(tmp_path):
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    file_path = local_dir / "hello.txt"
    file_path.write_text("hello")
    provider = FakeProvider()
    state = SyncState(str(tmp_path / "state.db"))

    first = sync(str(local_dir), provider, remote_root="backup", state=state)
    second = sync(str(local_dir), provider, remote_root="backup", state=state)

    assert first.uploaded == ["hello.txt"]
    assert second.skipped == ["hello.txt"]
    assert provider.calls[0][0:3:2] == ("upload", "backup/hello.txt")
    state.close()


def test_sync_updates_changed_files_and_deletes_removed_files(tmp_path):
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    file_path = local_dir / "hello.txt"
    file_path.write_text("hello")
    provider = FakeProvider()
    state = SyncState(str(tmp_path / "state.db"))

    sync(str(local_dir), provider, state=state)
    file_path.write_text("changed")
    updated = sync(str(local_dir), provider, state=state)
    file_path.unlink()
    deleted = sync(str(local_dir), provider, state=state)

    assert updated.updated == ["hello.txt"]
    assert deleted.deleted == ["hello.txt"]
    assert [call[0] for call in provider.calls] == ["upload", "update", "delete"]
    state.close()


def test_sync_with_concurrent_workers(tmp_path):
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    (local_dir / "file1.txt").write_text("content1")
    (local_dir / "file2.txt").write_text("content2")
    (local_dir / "file3.txt").write_text("content3")

    provider = FakeProvider()
    state = SyncState(str(tmp_path / "state.db"))

    result = sync(str(local_dir), provider, state=state, workers=3)

    assert set(result.uploaded) == {"file1.txt", "file2.txt", "file3.txt"}
    # Verify that the database was correctly updated for all files
    all_records = state.get_all()
    assert "file1.txt" in all_records
    assert "file2.txt" in all_records
    assert "file3.txt" in all_records
    state.close()
