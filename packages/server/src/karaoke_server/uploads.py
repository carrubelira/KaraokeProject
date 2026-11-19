"""Resumable uploads (plan v4 §7), in the spirit of tus: create, append from an offset, finish.

A browser on a flaky Wi-Fi resumes where it stopped: `HEAD` says how many bytes arrived, and the
next `PATCH` sends from there. When the last byte arrives the file goes into the blob store and
the upload answers with its hash; the temporary file is gone. Uploads nobody finished are
deleted after a day.
"""

import os
import secrets
import time
from pathlib import Path, PurePath

from karaoke_contracts import Blob
from karaoke_contracts.cas import BlobStore
from karaoke_server.db import Database
from karaoke_server.errors import ApiError

MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".txt": "text/plain",
}


class Uploads:
    def __init__(self, db: Database, folder: Path, store: BlobStore, max_bytes: int) -> None:
        self.db = db
        self.folder = folder
        self.store = store
        self.max_bytes = max_bytes
        folder.mkdir(parents=True, exist_ok=True)

    def _path(self, upload_id: str) -> Path:
        return self.folder / f"{upload_id}.part"

    def create(self, filename: str, size: int) -> dict[str, object]:
        name = PurePath(filename).name or "upload"
        if size <= 0:
            raise ApiError(422, "empty", "The file is empty")
        if size > self.max_bytes:
            raise ApiError(413, "too_big", "The file is too big", max_bytes=self.max_bytes)
        upload_id = "u_" + secrets.token_hex(8)
        self._path(upload_id).write_bytes(b"")
        self.db.execute(
            "INSERT INTO uploads (id, filename, size, created_at) VALUES (?, ?, ?, ?)",
            (upload_id, name, size, time.time()),
        )
        return self.get(upload_id)

    def get(self, upload_id: str) -> dict[str, object]:
        row = self.db.one("SELECT * FROM uploads WHERE id = ?", (upload_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such upload")
        return {
            "id": row["id"],
            "filename": row["filename"],
            "size": row["size"],
            "offset": row["received"],
            "blob": row["blob"],
        }

    def append(self, upload_id: str, offset: int, chunk: bytes) -> dict[str, object]:
        upload = self.get(upload_id)
        if upload["blob"] is not None:
            return upload
        if offset != upload["offset"]:
            raise ApiError(
                409, "bad_offset", "Resume from the offset HEAD gives", offset=upload["offset"]
            )
        size = int(upload["size"])  # type: ignore[call-overload]
        if offset + len(chunk) > size:
            raise ApiError(413, "too_big", "More bytes than announced")
        with self._path(upload_id).open("r+b") as file:
            file.seek(offset)
            file.write(chunk)
            file.flush()
            os.fsync(file.fileno())
        received = offset + len(chunk)
        blob_sha = None
        if received == size:
            blob_sha = self._finish(upload_id, str(upload["filename"])).sha256
        self.db.execute(
            "UPDATE uploads SET received = ?, blob = ? WHERE id = ?",
            (received, blob_sha, upload_id),
        )
        return self.get(upload_id)

    def _finish(self, upload_id: str, filename: str) -> Blob:
        media_type = MEDIA_TYPES.get(PurePath(filename).suffix.lower(), "application/octet-stream")
        path = self._path(upload_id)
        blob = self.store.put_file(path, media_type, link=True)
        path.unlink(missing_ok=True)
        return blob

    def purge(self, older_than: float = 86400) -> int:
        limit = time.time() - older_than
        rows = self.db.query(
            "SELECT id FROM uploads WHERE created_at < ? AND blob IS NULL", (limit,)
        )
        for row in rows:
            self._path(row["id"]).unlink(missing_ok=True)
        self.db.execute("DELETE FROM uploads WHERE created_at < ?", (limit,))
        return len(rows)
