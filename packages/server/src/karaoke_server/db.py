"""The server's SQLite database (plan v4 §3): contents, the task queue, nodes and playlists.

Blobs live on disk in the content store; the database knows which manifests exist, which tasks
are waiting, leased or done, which nodes are enrolled and what each player is set to. Every call
runs on the event loop's thread and takes well under a millisecond, so one connection is enough.
"""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Each entry upgrades the schema by one version; PRAGMA user_version says how many have run.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE contents (
        id TEXT PRIMARY KEY,
        manifest TEXT NOT NULL,
        version INTEGER NOT NULL,
        title TEXT NOT NULL,
        artist TEXT,
        language TEXT NOT NULL,
        duration REAL NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        deleted_at TEXT
    );
    CREATE TABLE manifests (
        sha256 TEXT PRIMARY KEY,
        content_id TEXT NOT NULL REFERENCES contents (id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (content_id, version)
    );
    CREATE TABLE jobs (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        state TEXT NOT NULL,
        params TEXT NOT NULL,
        result TEXT,
        error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE tasks (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
        kind TEXT NOT NULL,
        state TEXT NOT NULL,
        deps TEXT NOT NULL DEFAULT '[]',
        params TEXT NOT NULL DEFAULT '{}',
        inputs TEXT NOT NULL DEFAULT '[]',
        outputs TEXT NOT NULL DEFAULT '{}',
        data TEXT NOT NULL DEFAULT '{}',
        priority INTEGER NOT NULL DEFAULT 0,
        vram_mb INTEGER NOT NULL DEFAULT 0,
        needs_internet INTEGER NOT NULL DEFAULT 0,
        pinned_node TEXT,
        lease_id TEXT,
        node_id TEXT,
        lease_expires REAL,
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        stage TEXT,
        fraction REAL,
        error TEXT,
        error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        started_at REAL,
        finished_at REAL
    );
    CREATE INDEX tasks_by_state ON tasks (state, priority DESC, created_at);
    CREATE TABLE stage_times (
        kind TEXT NOT NULL,
        stage TEXT NOT NULL,
        seconds REAL NOT NULL,
        at REAL NOT NULL
    );
    CREATE TABLE operators (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        preferences TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE enrollments (
        token_hash TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        expires_at REAL NOT NULL,
        used_by TEXT
    );
    CREATE TABLE nodes (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        credential_hash TEXT NOT NULL UNIQUE,
        capabilities TEXT NOT NULL,
        config TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        last_seen REAL NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE playlists (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        version INTEGER NOT NULL,
        data TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE uploads (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        size INTEGER NOT NULL,
        received INTEGER NOT NULL DEFAULT 0,
        blob TEXT,
        created_at REAL NOT NULL
    );
    """,
]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: autocommit, with explicit transactions where several rows change.
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._depth = 0

    def migrate(self) -> None:
        version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
            with self.transaction():
                for statement in script.split(";"):
                    if statement.strip():
                        self._conn.execute(statement)
                self._conn.execute(f"PRAGMA user_version = {number}")

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> int:
        """Runs one statement; returns the number of rows it changed."""
        return self._conn.execute(sql, params).rowcount

    def query(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._depth:
            # Nested: the outer transaction commits or rolls back everything.
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        self._conn.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")
        finally:
            self._depth = 0

    def one(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self._conn.execute(sql, params).fetchone()
        return row

    def backup(self, dest: Path) -> None:
        """A consistent copy while the server keeps running.

        It reads through a connection of its own: it runs in a worker thread, and the server's
        connection belongs to the event loop (and may be inside a transaction).
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def close(self) -> None:
        self._conn.close()
