"""The worker's line to the server: plain HTTP on the LAN (decision 011), and blobs."""

import logging
from pathlib import Path
from typing import Any

import httpx

from karaoke_contracts.cas import BlobStore, HashMismatchError, sha256_file
from karaoke_contracts.nodes import (
    Capabilities,
    Enrolled,
    Enrollment,
    Heartbeat,
    Lease,
    TaskFailure,
    TaskLog,
    TaskProgress,
    TaskResult,
)

logger = logging.getLogger(__name__)

CHUNK = 1 << 20


def enrol(server: str, token: str, enrollment: Enrollment) -> Enrolled:
    """Enrols with a one-time token; the answer is this worker's own credential."""
    body = enrollment.model_copy(update={"token": token}).model_dump(mode="json")
    with httpx.Client(base_url=server, timeout=30) as client:
        answer = client.post("/api/nodes/enroll", json=body)
        answer.raise_for_status()
        return Enrolled.model_validate(answer.json())


class ServerClient:
    def __init__(
        self,
        server: str,
        credential: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.http = httpx.Client(
            base_url=server,
            headers={"Authorization": f"Bearer {credential}"},
            timeout=httpx.Timeout(30, read=60),
            transport=transport,
        )

    def close(self) -> None:
        self.http.close()

    def _json(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        answer = self.http.request(method, url, **kwargs)
        answer.raise_for_status()
        return answer

    def update_capabilities(self, capabilities: Capabilities) -> None:
        self._json("PUT", "/api/nodes/me/capabilities", json=capabilities.model_dump(mode="json"))

    def heartbeat(self, beat: Heartbeat) -> dict[str, Any]:
        data: dict[str, Any] = self._json(
            "POST", "/api/worker/heartbeat", json=beat.model_dump(mode="json")
        ).json()
        return data

    def lease(self, free_vram_mb: int | None, wait: bool = True) -> Lease | None:
        # While a song plays on the server's machine, the server holds GPU work back itself.
        answer = self._json(
            "POST", "/api/worker/lease", json={"free_vram_mb": free_vram_mb, "wait": wait}
        )
        return None if answer.status_code == 204 else Lease.model_validate(answer.json())

    def progress(self, lease: Lease, progress: TaskProgress) -> bool:
        answer = self._json(
            "POST",
            f"/api/tasks/{lease.task.id}/progress",
            json={"lease_id": lease.lease_id, "progress": progress.model_dump(mode="json")},
        )
        return bool(answer.json()["keep_going"])

    def log(self, lease: Lease, lines: list[str]) -> None:
        self._json(
            "POST",
            f"/api/tasks/{lease.task.id}/log",
            json={"lease_id": lease.lease_id, "log": TaskLog(lines=lines).model_dump(mode="json")},
        )

    def complete(self, lease: Lease, result: TaskResult) -> None:
        self._json(
            "POST",
            f"/api/tasks/{lease.task.id}/complete",
            json={"lease_id": lease.lease_id, "result": result.model_dump(mode="json")},
        )

    def fail(self, lease: Lease, failure: TaskFailure) -> None:
        self._json(
            "POST",
            f"/api/tasks/{lease.task.id}/fail",
            json={"lease_id": lease.lease_id, "failure": failure.model_dump(mode="json")},
        )

    def json(self, url: str) -> Any:
        return self._json("GET", url).json()

    def local_path(self, sha256: str) -> Path | None:
        answer = self.http.get(f"/api/blobs/{sha256}/local")
        if answer.status_code != 200:
            return None
        path = Path(answer.json()["path"])
        return path if path.is_file() else None

    def download(self, sha256: str, store: BlobStore) -> Path:
        """Brings a blob into the local store (resuming a partial download), checked."""
        if store.has(sha256):
            return store.path(sha256)
        partial = store.root / "tmp" / f"{sha256}.part"
        partial.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(3):
            have = partial.stat().st_size if partial.exists() else 0
            headers = {"Range": f"bytes={have}-"} if have else {}
            with self.http.stream("GET", f"/api/blobs/{sha256}", headers=headers) as answer:
                if answer.status_code == 416:
                    partial.unlink(missing_ok=True)
                    continue
                answer.raise_for_status()
                mode = "ab" if answer.status_code == 206 else "wb"
                with partial.open(mode) as out:
                    for chunk in answer.iter_bytes(CHUNK):
                        out.write(chunk)
            if sha256_file(partial) == sha256:
                dest = store.path(sha256)
                dest.parent.mkdir(parents=True, exist_ok=True)
                partial.replace(dest)
                return dest
            partial.unlink(missing_ok=True)
        raise HashMismatchError(sha256, "a corrupt download, three times")

    def upload(self, path: Path, sha256: str | None = None) -> str:
        sha = sha256 or sha256_file(path)
        head = self.http.head(f"/api/blobs/{sha}")
        if head.status_code == 200:
            return sha
        with path.open("rb") as body:
            self._json("PUT", f"/api/blobs/{sha}", content=iter(lambda: body.read(CHUNK), b""))
        return sha
