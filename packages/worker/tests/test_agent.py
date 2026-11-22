"""A worker against a real server app: enrolment, a song analysed, reviewed and made end to end,
an export, the live log, and cancellation, with the fake engine (no GPU)."""

import asyncio
import time
from pathlib import Path
from typing import Any

import httpx
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


class _Buffered(httpx.BaseTransport):
    """The app's test transport, its answers read in full: httpx's own client wants a sync
    stream, which starlette's transport no longer hands over."""

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        answer = self.inner.handle_request(request)
        return httpx.Response(
            answer.status_code, headers=answer.headers, content=answer.read(), request=request
        )


class Rig:
    def __init__(self, tmp_path: Path) -> None:
        settings = Settings.from_env(
            data_dir=tmp_path / "server", web_dir=None, audio="off", lease_wait_seconds=0.0
        )
        self.services = build_services(settings)
        self.app = create_app(settings, services=self.services)
        self.http = TestClient(self.app)
        self.operator = TestClient(
            self.app, headers={"Authorization": f"Bearer {self.services.auth.add_operator('op')}"}
        )
        token = self.services.auth.new_enrollment("worker")
        caps = Capabilities(os="linux", gpus=[Gpu(name="fake", vram_total_mb=8192)], internet=True,
                            tasks=["fetch", "analyze", "make", "render"])  # fmt: skip
        enrolled = self.http.post(
            "/api/nodes/enroll",
            json=Enrollment(token=token, kind="worker", name="w", capabilities=caps).model_dump(
                mode="json"
            ),
        ).json()
        client = ServerClient(
            "http://testserver", enrolled["credential"], transport=_Buffered(self.http._transport)
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

    def confirm(self, job_id: str, **choice: Any) -> None:
        body = {"title": "Proba", "language": "gl", "lyrics": "la la", **choice}
        answer = self.operator.post(f"/api/jobs/{job_id}/confirm", json=body)
        assert answer.status_code == 200, answer.text


async def test_a_karaoke_is_made_and_exported_by_a_worker(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    body = {"upload": rig.upload(b"ID3" + bytes(500)), "lyrics": "la la", "title": "Proba"}
    job = rig.operator.post("/api/jobs", json=body).json()
    review = await rig.until(job["id"], ("review", "failed"))
    assert review["state"] == "review", review
    assert review["tasks"][0]["data"]["best"]["title"] == "Proba"
    rig.confirm(job["id"])
    done = await rig.until(job["id"], ("done", "failed"))
    assert done["state"] == "done", done
    make = done["tasks"][1]
    assert make["log"], "the whole log went up as a blob"
    log = rig.operator.get(f"/api/jobs/{job['id']}/tasks/make/log").text
    assert "── separate" in log
    assert all(t["error"] is None for t in done["tasks"])
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
    await rig.until(job["id"], ("review",))
    rig.confirm(job["id"])
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


async def test_an_engine_failure_is_reported_with_its_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KARAOKE_ACOUSTID_KEY", raising=False)
    monkeypatch.setattr("karaoke_worker.identify.find_lyrics", lambda guess, duration: [])
    rig = Rig(tmp_path)
    rig.ctx.fake = False  # the real engine cannot read these bytes
    job = rig.operator.post(
        "/api/jobs", json={"upload": rig.upload(b"not audio" * 10, "Banda - Cantiga.mp3")}
    ).json()
    review = await rig.until(job["id"], ("review", "failed"))
    analysis = review["tasks"][0]["data"]
    assert (analysis["best"]["title"], analysis["best"]["artist"]) == ("Cantiga", "Banda")
    assert analysis["fingerprint"] == "no_key"
    rig.confirm(job["id"], lyrics="x")
    rig.services.db.execute("UPDATE tasks SET max_attempts = 1")
    failed = await rig.until(job["id"], ("failed", "done"))
    assert failed["state"] == "failed"
    make = failed["tasks"][1]
    assert make["error_code"] in ("unreadable", "engine_failed")
    assert make["log"], "a failed task still leaves its log"


async def test_with_its_cpu_slots_full_it_asks_only_for_gpu_work(tmp_path: Path) -> None:
    from karaoke_worker.agent import CPU_SLOTS, Running

    asked: list[bool] = []

    class Client:
        def lease(self, free: int | None, wait: bool = True, *, cpu: bool = True) -> None:
            asked.append(cpu)

    ctx = Context(client=Client(), store=BlobStore(tmp_path), work=tmp_path,
                  spawner=None, downloader=None, fake=True)  # fmt: skip
    agent = Agent(ctx)
    idle = asyncio.create_task(asyncio.sleep(60))
    try:
        await agent.lease_once()
        for i in range(CPU_SLOTS):
            agent.running[f"t{i}"] = Running(lease=None, task=idle, gpu=False)
        await agent.lease_once()
        agent.running["g"] = Running(lease=None, task=idle, gpu=True)
        assert await agent.lease_once() is None
    finally:
        idle.cancel()
    assert asked == [True, False], "no lease at all once the GPU is busy too"
