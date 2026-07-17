from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

SCHEMA_VERSION = 2


@dataclass(frozen=True)
class SyncRecord:
    remote_id: str
    hash: Optional[str]
    size: int
    mtime: float


@dataclass(frozen=True)
class SyncJob:
    id: str
    local_root: str
    provider: str
    remote_root: str


class SyncState(AbstractContextManager["SyncState"]):
    """SQLite state isolated by local root, provider destination, and remote root."""

    def __init__(self, db_path: str = ".cloudsync_state.db"):
        self.db_path = str(Path(db_path).expanduser().resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(sync_state)")}
        if columns and "job_id" not in columns:
            self.conn.execute("ALTER TABLE sync_state RENAME TO legacy_sync_state")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_jobs (
                id TEXT PRIMARY KEY,
                local_root TEXT NOT NULL,
                provider TEXT NOT NULL,
                remote_root TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(local_root, provider, remote_root)
            );
            CREATE TABLE IF NOT EXISTS sync_state (
                job_id TEXT NOT NULL REFERENCES sync_jobs(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                remote_id TEXT NOT NULL,
                hash TEXT,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                PRIMARY KEY(job_id, path)
            );
            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES sync_jobs(id),
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                status TEXT NOT NULL,
                error TEXT
            );
            """
        )
        if version < SCHEMA_VERSION:
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.conn.commit()

    @staticmethod
    def job_id(local_root: str, provider: str, remote_root: str) -> str:
        payload = json.dumps(
            [str(Path(local_root).expanduser().resolve()), provider, remote_root.strip("/")],
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:24]

    def ensure_job(self, local_root: str, provider: str, remote_root: str) -> SyncJob:
        local_root = str(Path(local_root).expanduser().resolve())
        remote_root = remote_root.strip("/")
        job_id = self.job_id(local_root, provider, remote_root)
        self.conn.execute(
            "INSERT OR IGNORE INTO sync_jobs(id, local_root, provider, remote_root) VALUES (?, ?, ?, ?)",
            (job_id, local_root, provider, remote_root),
        )
        self.conn.commit()
        return SyncJob(job_id, local_root, provider, remote_root)

    def get(self, path: str, job_id: str) -> Optional[SyncRecord]:
        row = self.conn.execute(
            "SELECT remote_id, hash, size, mtime FROM sync_state WHERE job_id = ? AND path = ?",
            (job_id, path),
        ).fetchone()
        return SyncRecord(*row) if row else None

    def get_all(self, job_id: str) -> Dict[str, SyncRecord]:
        rows = self.conn.execute(
            "SELECT path, remote_id, hash, size, mtime FROM sync_state WHERE job_id = ?",
            (job_id,),
        ).fetchall()
        return {row[0]: SyncRecord(*row[1:]) for row in rows}

    def set(
        self, path: str, remote_id: str, hash: Optional[str], size: int, mtime: float, job_id: str
    ) -> None:
        self.conn.execute(
            """INSERT INTO sync_state(job_id, path, remote_id, hash, size, mtime)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id, path) DO UPDATE SET remote_id=excluded.remote_id,
               hash=excluded.hash, size=excluded.size, mtime=excluded.mtime""",
            (job_id, path, remote_id, hash, size, mtime),
        )

    def delete(self, path: str, job_id: str) -> None:
        self.conn.execute("DELETE FROM sync_state WHERE job_id = ? AND path = ?", (job_id, path))

    def begin_run(self, job_id: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO sync_runs(job_id, status) VALUES (?, 'running')", (job_id,)
        )
        self.conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("Could not record synchronization run")
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, error: Optional[str] = None) -> None:
        self.conn.execute(
            "UPDATE sync_runs SET completed_at=CURRENT_TIMESTAMP, status=?, error=? WHERE id=?",
            (status, error, run_id),
        )
        self.conn.commit()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            self.conn.rollback()
        self.close()
