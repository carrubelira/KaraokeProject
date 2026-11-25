"""The song library (plan v4 §3): contents, their manifest versions, the trash and the blob GC.

A content is a song; each version is a manifest in the blob store. The library keeps which
version is current, which ones exist, and which contents are in the trash (30 days, then gone).
A blob is kept while any manifest of a content that is not purged, any unfinished task or any
upload refers to it; the rest is collected.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from karaoke_contracts import Manifest
from karaoke_contracts.cas import BlobStore
from karaoke_server.clock import iso_now
from karaoke_server.db import Database
from karaoke_server.errors import ApiError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GcReport:
    kept: int
    deleted: int
    freed_bytes: int
    purged_contents: int


def content_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "manifest": row["manifest"],
        "version": row["version"],
        "title": row["title"],
        "artist": row["artist"],
        "language": row["language"],
        "duration": row["duration"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "deleted_at": row["deleted_at"],
    }


class Library:
    def __init__(self, db: Database, store: BlobStore, trash_days: int = 30) -> None:
        self.db = db
        self.store = store
        self.trash_days = trash_days

    def manifest(self, sha256: str) -> Manifest:
        if not self.store.has(sha256):
            raise ApiError(404, "not_found", "No such manifest")
        return Manifest.model_validate_json(self.store.read_bytes(sha256))

    def register(self, sha256: str) -> dict[str, Any]:
        """Makes a stored manifest the current version of its content."""
        manifest = self.manifest(sha256)
        now = iso_now()
        with self.db.transaction():
            current = self.db.one("SELECT * FROM contents WHERE id = ?", (manifest.content_id,))
            if current is not None and current["version"] >= manifest.version:
                # A new song with the id of an existing one: it becomes its next version.
                bumped = manifest.model_copy(
                    update={"version": current["version"] + 1, "parent": current["manifest"]}
                )
                from karaoke_contracts import canonical_json

                blob = self.store.put_bytes(
                    canonical_json(bumped), "application/vnd.karaoke.manifest+json"
                )
                manifest, sha256 = bumped, blob.sha256
            self.db.execute(
                "INSERT INTO contents (id, manifest, version, title, artist, language, duration,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (id) DO UPDATE SET manifest = excluded.manifest,"
                " version = excluded.version, title = excluded.title, artist = excluded.artist,"
                " language = excluded.language, duration = excluded.duration,"
                " updated_at = excluded.updated_at, deleted_at = NULL",
                (
                    manifest.content_id,
                    sha256,
                    manifest.version,
                    manifest.title,
                    manifest.artist,
                    manifest.language,
                    manifest.duration,
                    now,
                    now,
                ),
            )
            self.db.execute(
                "INSERT OR IGNORE INTO manifests (sha256, content_id, version, created_at)"
                " VALUES (?, ?, ?, ?)",
                (sha256, manifest.content_id, manifest.version, now),
            )
        return self.get(manifest.content_id)

    def get(self, content_id: str) -> dict[str, Any]:
        row = self.db.one("SELECT * FROM contents WHERE id = ?", (content_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such song")
        return content_row(row)

    def contents(self, *, trash: bool = False) -> list[dict[str, Any]]:
        where = "deleted_at IS NOT NULL" if trash else "deleted_at IS NULL"
        rows = self.db.query(f"SELECT * FROM contents WHERE {where} ORDER BY title COLLATE NOCASE")  # noqa: S608
        return [content_row(r) for r in rows]

    def versions(self, content_id: str) -> list[dict[str, Any]]:
        self.get(content_id)
        rows = self.db.query(
            "SELECT sha256, version, created_at FROM manifests WHERE content_id = ?"
            " ORDER BY version DESC",
            (content_id,),
        )
        return [dict(r) for r in rows]

    def trash(self, content_id: str) -> None:
        if not self.db.execute(
            "UPDATE contents SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (iso_now(), content_id),
        ):
            raise ApiError(404, "not_found", "No such song")

    def restore(self, content_id: str) -> None:
        if not self.db.execute(
            "UPDATE contents SET deleted_at = NULL WHERE id = ? AND deleted_at IS NOT NULL",
            (content_id,),
        ):
            raise ApiError(404, "not_found", "No such song in the trash")

    def purge_trash(self, now: datetime | None = None, *, everything: bool = False) -> int:
        limit = (now or datetime.now(UTC)) - timedelta(days=self.trash_days)
        if everything:
            return self.db.execute("DELETE FROM contents WHERE deleted_at IS NOT NULL")
        return self.db.execute(
            "DELETE FROM contents WHERE deleted_at IS NOT NULL AND deleted_at < ?",
            (limit.isoformat(timespec="seconds"),),
        )

    def referenced(self) -> set[str]:
        """Every blob something still needs."""
        keep: set[str] = set()
        for row in self.db.query("SELECT sha256 FROM manifests"):
            keep.add(row["sha256"])
            try:
                keep.update(b.sha256 for b in self.manifest(row["sha256"]).blobs())
            except ApiError:
                logger.warning("manifest %s is missing from the store", row["sha256"])
        for row in self.db.query(
            "SELECT inputs, outputs FROM tasks WHERE state NOT IN ('done', 'failed', 'cancelled')"
            " OR finished_at > ?",
            (time.time() - 86400,),
        ):
            keep.update(json.loads(row["inputs"]))
            keep.update(json.loads(row["outputs"]).values())
        for row in self.db.query("SELECT blob FROM uploads WHERE blob IS NOT NULL"):
            keep.add(row["blob"])
        return keep

    def collect(self, quota_bytes: int | None = None, *, grace_seconds: float = 3600) -> GcReport:
        """Deletes unreferenced blobs older than `grace_seconds` (a blob a worker just uploaded
        may not be in a manifest yet); over the quota, the trash is emptied first."""
        purged = self.purge_trash()
        if quota_bytes is not None and self.usage() > quota_bytes:
            purged += self.purge_trash(everything=True)
        keep = self.referenced()
        deleted = freed = kept = 0
        cutoff = time.time() - grace_seconds
        for sha in list(self.store.all()):
            if sha in keep:
                kept += 1
                continue
            path = self.store.path(sha)
            stat = path.stat()
            if stat.st_mtime > cutoff:
                kept += 1
                continue
            self.store.delete(sha)
            deleted += 1
            freed += stat.st_size
        return GcReport(kept, deleted, freed, purged)

    def usage(self) -> int:
        return sum(self.store.path(s).stat().st_size for s in self.store.all())
