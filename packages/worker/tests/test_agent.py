"""A worker against a real server app: enrolment, a karaoke made end to end, an export, and
cancellation, with the fake engine (no GPU)."""

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from karaoke_contracts.cas import BlobStore
from karaoke_contracts.nodes import Capabilities, Enrollment, Gpu
from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_worker.agent import Agent
from karaoke_worker.child import ProcessSpawner, SpawnSettings
from karaoke_worker.client import ServerClient
from karaoke_worker.download import YtDlp
from karaoke_worker.tasks import Context

pytestmark = [pytest.mark.usefixtures("ffmpeg"), pytest.mark.anyio]


class Rig:
    def __init__(self, tmp_path: Path) -> None:
        settings = Settings.from_env(
            data_dir=tmp_path / "server", web_dir=None, tls=False, lease_wait_seconds=0.0
        )
        self.services = build_services(settings)
        self.app = create_app(settings, services=self.services)
        self.http = TestClient(self.app)
        self.operator = TestClient(
            self.app, headers={"Authorization": f"Bearer {self.services.auth.add_operator('op')}"}
        )
        token = self.services.auth.new_enrollment("worker")
        caps = Capabilities(os="linux", gpus=[Gpu(name="fake", vram_total_mb=8192)], internet=True,
                            tasks=["fetch", "make", "render"])  # fmt: skip
        enrolled = self.http.post(
            "/api/nodes/enroll",
            json=Enrollment(token=token, kind="worker", name="w", capabilities=caps).model_dump(
                mode="json"
            ),
        ).json()
        client = ServerClient(
            "http://testserver", enrolled["credential"], transport=self.http._transport
        )
        data = tmp_path / "worker"
        self.ctx = Context(
            client=client,
            store=BlobStore(data / "blobs"),
            work=data / "work",
            spawner=ProcessSpawner(SpawnSettings(data_dir=data)),
            downloader=YtDlp(("false",)),
            fake=True,
        )
        (data / "tmp").mkdir(parents=True, exist_ok=True)
        self.agent = Agent(self.ctx, lease_wait=False, heartbeat_seconds=0.2)

    def upload(self, data: bytes, name: str = "song.mp3") -> str:
        upload = self.operator.post(
            "/api/uploads", json={"filename": name, "size": len(data)}
        ).json()
        self.operator.patch(
            f"/api/uploads/{upload['id']}", content=data, headers={"Upload-Offset": "0"}
        )
        return str(upload["id"])

    async def until(
        self, job_id: str, states: tuple[str, ...], seconds: float = 90
    ) -> dict[str, Any]:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not self.agent.running:
                await self.agent.lease_once()
            await asyncio.sleep(0.1)
            job: dict[str, Any] = self.operator.get(f"/api/jobs/{job_id}").json()
            if job["state"] in states:
                return job
        raise AssertionError(f"job still {job['state']}: {job}")


async def test_a_karaoke_is_made_and_exported_by_a_worker(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    body = {"upload": rig.upload(b"ID3" + bytes(500)), "lyrics": "la la", "title": "Proba"}
    job = rig.operator.post("/api/jobs", json=body).json()
    done = await rig.until(job["id"], ("done", "failed"))
    assert done["state"] == "done", done
    content = rig.operator.get(f"/api/contents/{done['result']['content_id']}").json()
    assert content["title"] == "Proba"
    manifest = rig.operator.get(f"/api/contents/{content['id']}/manifest").json()
    for track in manifest["tracks"]:
        assert rig.services.store.verify(track["blob"]["sha256"])
    export = rig.operator.post(
        "/api/jobs", json={"kind": "render", "content_id": content["id"]}
    ).json()
    exported = await rig.until(export["id"], ("done", "failed"))
    assert exported["state"] == "done", exported
    assert rig.services.store.has(exported["result"]["outputs"]["video"])


async def test_cancelling_stops_the_running_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KARAOKE_FAKE_STAGE_SECONDS", "2")
    rig = Rig(tmp_path)
    job = rig.operator.post("/api/jobs", json={"upload": rig.upload(b"x" * 100)}).json()
    await rig.agent.lease_once()
    assert rig.agent.running
    await asyncio.sleep(0.5)
    rig.operator.post(f"/api/jobs/{job['id']}/cancel")
    await rig.agent.heartbeat_once()
    for _ in range(100):
        if not rig.agent.running:
            break
        await asyncio.sleep(0.05)
    assert not rig.agent.running
    assert rig.operator.get(f"/api/jobs/{job['id']}").json()["state"] == "cancelled"


async def test_an_engine_failure_is_reported(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    rig.ctx.fake = False  # the real engine cannot read these bytes
    job = rig.operator.post(
        "/api/jobs", json={"upload": rig.upload(b"not audio" * 10), "lyrics": "x"}
    ).json()
    rig.services.db.execute("UPDATE tasks SET max_attempts = 1")
    failed = await rig.until(job["id"], ("failed", "done"))
    assert failed["state"] == "failed"
    assert failed["tasks"][0]["error_code"] in ("unreadable", "engine_failed")
