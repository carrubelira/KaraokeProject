"""Content-addressed storage helpers shared by the server, the workers and the migrator.

A blob lives at `<root>/<first two hex digits>/<the other 62>`; the hash is SHA-256 of its bytes.
Writing goes through a temporary file in the same folder and an atomic rename, so a reader never
sees half a blob and two writers of the same blob end with the same file.
"""

import hashlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from karaoke_contracts.manifest import Blob

CHUNK = 1 << 20


def blob_path(root: Path, sha256: str) -> Path:
    return root / sha256[:2] / sha256[2:]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class HashMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class BlobStore:
    """A folder of blobs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, sha256: str) -> Path:
        return blob_path(self.root, sha256)

    def has(self, sha256: str) -> bool:
        return self.path(sha256).is_file()

    def put_bytes(self, data: bytes, media_type: str) -> Blob:
        return self.put_chunks([data], media_type)

    def put_file(self, src: Path, media_type: str, *, link: bool = False) -> Blob:
        """Copies (or hard-links, on the same disk) a file into the store."""
        sha = sha256_file(src)
        dest = self.path(sha)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if link:
                try:
                    os.link(src, dest)
                    return Blob(sha256=sha, size=dest.stat().st_size, media_type=media_type)
                except OSError:
                    pass
            with src.open("rb") as file:
                self._write(iter(lambda: file.read(CHUNK), b""), expected=sha)
        return Blob(sha256=sha, size=dest.stat().st_size, media_type=media_type)

    def put_chunks(
        self, chunks: Iterable[bytes], media_type: str, expected: str | None = None
    ) -> Blob:
        sha, size = self._write(chunks, expected)
        return Blob(sha256=sha, size=size, media_type=media_type)

    def _write(self, chunks: Iterable[bytes], expected: str | None) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        tmp_dir = self.root / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        fd, name = tempfile.mkstemp(dir=tmp_dir)
        try:
            with os.fdopen(fd, "wb") as out:
                for chunk in chunks:
                    digest.update(chunk)
                    size += len(chunk)
                    out.write(chunk)
            sha = digest.hexdigest()
            if expected is not None and sha != expected:
                raise HashMismatchError(expected, sha)
            dest = self.path(sha)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(name, dest)
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise
        return sha, size

    def read_bytes(self, sha256: str) -> bytes:
        return self.path(sha256).read_bytes()

    def verify(self, sha256: str) -> bool:
        return self.has(sha256) and sha256_file(self.path(sha256)) == sha256

    def all(self) -> Iterator[str]:
        for folder in self.root.iterdir():
            if len(folder.name) == 2 and folder.is_dir():
                for file in folder.iterdir():
                    yield folder.name + file.name

    def delete(self, sha256: str) -> None:
        self.path(sha256).unlink(missing_ok=True)
