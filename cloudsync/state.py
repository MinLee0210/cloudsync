import sqlite3
from typing import Dict, Optional, NamedTuple


class SyncRecord(NamedTuple):
    remote_id: str
    hash: str
    size: int
    mtime: float


class SyncState:
    """Persists the last-known mapping of local path -> remote file info."""

    def __init__(self, db_path: str = ".cloudsync_state.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                path TEXT PRIMARY KEY,
                remote_id TEXT NOT NULL,
                hash TEXT,
                size INTEGER,
                mtime REAL
            )
        """)
        self.conn.commit()

    def get(self, path: str) -> Optional[SyncRecord]:
        row = self.conn.execute(
            "SELECT remote_id, hash, size, mtime FROM sync_state WHERE path = ?",
            (path,),
        ).fetchone()
        return SyncRecord(*row) if row else None

    def get_all(self) -> Dict[str, SyncRecord]:
        rows = self.conn.execute(
            "SELECT path, remote_id, hash, size, mtime FROM sync_state"
        ).fetchall()
        return {r[0]: SyncRecord(*r[1:]) for r in rows}

    def set(
        self, path: str, remote_id: str, hash: str, size: int, mtime: float
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO sync_state (path, remote_id, hash, size, mtime) VALUES (?, ?, ?, ?, ?)",
            (path, remote_id, hash, size, mtime),
        )
        self.conn.commit()

    def delete(self, path: str) -> None:
        self.conn.execute("DELETE FROM sync_state WHERE path = ?", (path,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
