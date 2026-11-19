"""The task queue end to end over the API, with fake workers."""

import time
from typing import Any

from fastapi.testclient import TestClient

from karaoke_server.services import Services

from .conftest import Clients


def _upload(clients: Clients, data: bytes = b"song" * 100) -> str:
    op = clients.operator()
    upload = op.post("/api/uploads", json={"filename": "song.mp3", "size": len(data)}).json()
    op.patch(f"/api/uploads/{upload['id']}", content=data, headers={"Upload-Offset": "0"})
    return str(upload["id"])


def _lease(worker: TestClient, **body: Any) -> dict[str, Any] | None:
    answer = worker.post("/api/worker/lease", json={"wait": False, **body})
    assert answer.status_code in (200, 204), answer.text
    return answer.json() if answer.status_code == 200 else None


def _finish(worker: TestClient, lease: dict[str, Any], outputs: dict[str, str]) -> None:
    task = lease["task"]["id"]
    answer = worker.post(
        f"/api/tasks/{task}/complete",
        json={"lease_id": lease["lease_id"], "result": {"outputs": outputs, "data": {}}},
    )
    assert answer.status_code == 204, answer.text


def test_an_upload_becomes_a_song(clients: Clients, demo_manifest: str) -> None:
    op = clients.operator()
    job = op.post(
        "/api/jobs", json={"upload": _upload(clients), "lyrics": "la la", "language": "gl"}
    ).json()
    assert [t["kind"] for t in job["tasks"]] == ["make"]
    _, worker = clients.enrol("worker")
    lease = _lease(worker, free_vram_mb=4000)
    assert lease is not None
    assert lease["task"]["kind"] == "make"
    assert lease["task"]["params"]["lyrics"] == "la la"
    assert lease["task"]["inputs"] == [job["params"]["source"]]
    progress = worker.post(
        f"/api/tasks/{lease['task']['id']}/progress",
        json={"lease_id": lease["lease_id"], "progress": {"stage": "separate", "fraction": 0.4}},
    )
    assert progress.json() == {"keep_going": True}
    assert op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]["state"] == "running"
    _finish(worker, lease, {"manifest": demo_manifest})
    done = op.get(f"/api/jobs/{job['id']}").json()
    assert done["state"] == "done"
    assert done["result"]["content_id"] == "demo"
    assert [c["id"] for c in op.get("/api/contents").json()] == ["demo"]
    assert op.get("/api/contents/demo/manifest").json()["content_id"] == "demo"
    assert op.get("/api/contents/demo/lyrics").json()["lines"]


def test_a_link_is_fetched_then_made_on_the_same_worker(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v", "lrclib": False}).json()
    assert [t["state"] for t in job["tasks"]] == ["ready", "waiting"]
    _, offline = clients.enrol("worker", name="offline", internet=False)
    assert _lease(offline) is None, "fetch needs internet"
    _, online = clients.enrol("worker", name="online")
    fetch = _lease(online)
    assert fetch is not None
    assert fetch["task"]["kind"] == "fetch"
    source = clients.services.store.put_bytes(b"downloaded", "audio/mpeg").sha256
    _finish(online, fetch, {"source": source})
    make = _lease(online)
    assert make is not None
    assert make["task"]["kind"] == "make"
    assert make["task"]["inputs"] == [source]
    assert make["task"]["params"]["from"]["fetch"]["source"] == source


def test_affinity_prefers_the_worker_that_made_the_inputs(
    clients: Clients, services: Services
) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    first_id, first = clients.enrol("worker", name="first")
    second_id, second = clients.enrol("worker", name="second")
    fetch = _lease(first)
    assert fetch is not None
    _finish(first, fetch, {"source": services.store.put_bytes(b"x", "audio/mpeg").sha256})
    make = services.db.one("SELECT * FROM tasks WHERE id = ?", (f"{job['id']}:make",))
    assert services.queue._affinity(make, first_id) == 1
    assert services.queue._affinity(make, second_id) == 0
    # A later job of the same priority is created after; `second` still gets work.
    op.post("/api/jobs", json={"url": "https://example.com/w"})
    assert _lease(first) is not None
    assert _lease(second) is not None


def test_a_worker_that_vanishes_loses_its_task(clients: Clients, services: Services) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, lost = clients.enrol("worker", name="lost")
    lease = _lease(lost)
    assert lease is not None
    assert services.queue.expire(now=time.time() + 60) == 1
    _, other = clients.enrol("worker", name="other")
    again = _lease(other)
    assert again is not None
    assert again["task"]["id"] == lease["task"]["id"]
    # The old lease is refused.
    late = lost.post(
        f"/api/tasks/{lease['task']['id']}/complete",
        json={"lease_id": lease["lease_id"], "result": {"outputs": {}, "data": {}}},
    )
    assert late.status_code == 409
    assert op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]["attempts"] == 2


def test_heartbeat_renews_and_tells_to_stop_cancelled_tasks(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, worker = clients.enrol("worker")
    lease = _lease(worker)
    assert lease is not None
    task = lease["task"]["id"]
    beat = worker.post(
        "/api/worker/heartbeat", json={"running": [task], "telemetry": {"gpu_util": 90}}
    )
    assert beat.json()["stop"] == []
    assert op.get("/api/nodes").json()[0]["telemetry"]["gpu_util"] == 90
    op.post(f"/api/jobs/{job['id']}/cancel")
    assert worker.post("/api/worker/heartbeat", json={"running": [task]}).json()["stop"] == [task]


def test_capabilities_filter_tasks(clients: Clients) -> None:
    op = clients.operator()
    op.post("/api/jobs", json={"upload": _upload(clients)})
    _, small = clients.enrol("worker", name="small", gpus=[{"name": "GT", "vram_total_mb": 2048}])
    assert _lease(small) is None, "make needs 3.2 GB"
    _, cpu = clients.enrol("worker", name="cpu", gpus=[])
    assert _lease(cpu) is None
    _, big = clients.enrol("worker", name="big")
    assert _lease(big, busy_playing=True) is None, "a player is playing on that machine"
    assert _lease(big) is not None


def test_priority_pause_resume_and_pin(clients: Clients) -> None:
    op = clients.operator()
    low = op.post("/api/jobs", json={"upload": _upload(clients), "batch": True}).json()
    high = op.post("/api/jobs", json={"upload": _upload(clients, b"other" * 10)}).json()
    _, worker = clients.enrol("worker", name="w1")
    _, other = clients.enrol("worker", name="w2")
    op.post(f"/api/jobs/{high['id']}/pause")
    op.patch(f"/api/jobs/{low['id']}", json={"pinned_node": "nobody"})
    assert _lease(worker) is None
    op.post(f"/api/jobs/{high['id']}/resume")
    first = _lease(worker)
    assert first is not None
    assert first["task"]["job_id"] == high["id"]
    op.patch(f"/api/jobs/{low['id']}", json={"unpin": True, "priority": 50})
    second = _lease(other)
    assert second is not None
    assert second["task"]["job_id"] == low["id"]


def test_failure_retries_then_fails_and_can_be_retried(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, worker = clients.enrol("worker")
    for attempt in range(3):
        lease = _lease(worker)
        assert lease is not None, attempt
        worker.post(
            f"/api/tasks/{lease['task']['id']}/fail",
            json={
                "lease_id": lease["lease_id"],
                "failure": {"code": "gpu_memory", "message": "OOM"},
            },
        )
    failed = op.get(f"/api/jobs/{job['id']}").json()
    assert failed["state"] == "failed"
    assert failed["tasks"][0]["error_code"] == "gpu_memory"
    assert _lease(worker) is None
    assert op.post(f"/api/jobs/{job['id']}/retry").json()["state"] == "active"
    assert _lease(worker) is not None


def test_a_job_needs_a_finished_upload_or_a_link(clients: Clients) -> None:
    op = clients.operator()
    upload = op.post("/api/uploads", json={"filename": "a.mp3", "size": 10}).json()
    assert op.post("/api/jobs", json={"upload": upload["id"]}).status_code == 409
    assert op.post("/api/jobs", json={}).status_code == 422
    assert op.post("/api/jobs", json={"url": "ftp://x"}).status_code == 422


def test_completing_needs_the_outputs_uploaded(clients: Clients) -> None:
    op = clients.operator()
    op.post("/api/jobs", json={"upload": _upload(clients)})
    _, worker = clients.enrol("worker")
    lease = _lease(worker)
    assert lease is not None
    answer = worker.post(
        f"/api/tasks/{lease['task']['id']}/complete",
        json={"lease_id": lease["lease_id"], "result": {"outputs": {"manifest": "a" * 64}}},
    )
    assert answer.status_code == 409
    assert answer.json()["missing"] == ["a" * 64]


def test_render_job_exports_the_current_version(clients: Clients, demo_manifest: str) -> None:
    clients.services.library.register(demo_manifest)
    op = clients.operator()
    job = op.post("/api/jobs", json={"kind": "render", "content_id": "demo", "vocals": 0.3}).json()
    assert job["tasks"][0]["kind"] == "render"
    _, worker = clients.enrol("worker")
    lease = _lease(worker)
    assert lease is not None
    assert lease["task"]["inputs"] == [demo_manifest]
    video = clients.services.store.put_bytes(b"mp4", "video/mp4").sha256
    _finish(worker, lease, {"video": video})
    assert op.get(f"/api/jobs/{job['id']}").json()["result"]["outputs"] == {"video": video}
