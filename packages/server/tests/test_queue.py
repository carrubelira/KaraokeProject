"""The task queue end to end over the API, with fake workers."""

import time
from typing import Any

from fastapi.testclient import TestClient

from karaoke_server.services import Services

from .conftest import Clients

ANALYSIS = {
    "best": {"title": "Pálida Luna", "artist": "Los Suaves", "language": "es",
             "confidence": 0.9, "source": "acoustid"},
    "lyrics": [{"id": 7, "text": "la la", "synced": False, "source": "lrclib"}],
}  # fmt: skip


def _upload(clients: Clients, data: bytes = b"song" * 100) -> str:
    op = clients.operator()
    upload = op.post("/api/uploads", json={"filename": "song.mp3", "size": len(data)}).json()
    op.patch(f"/api/uploads/{upload['id']}", content=data, headers={"Upload-Offset": "0"})
    return str(upload["id"])


def _lease(worker: TestClient, **body: Any) -> dict[str, Any] | None:
    answer = worker.post("/api/worker/lease", json={"wait": False, **body})
    assert answer.status_code in (200, 204), answer.text
    return answer.json() if answer.status_code == 200 else None


def _finish(
    worker: TestClient,
    lease: dict[str, Any],
    outputs: dict[str, str],
    data: dict[str, Any] | None = None,
) -> None:
    task = lease["task"]["id"]
    answer = worker.post(
        f"/api/tasks/{task}/complete",
        json={"lease_id": lease["lease_id"], "result": {"outputs": outputs, "data": data or {}}},
    )
    assert answer.status_code == 204, answer.text


def _progress(worker: TestClient, lease: dict[str, Any], **progress: Any) -> Any:
    return worker.post(
        f"/api/tasks/{lease['task']['id']}/progress",
        json={"lease_id": lease["lease_id"], "progress": progress},
    )


def _analyse(worker: TestClient) -> dict[str, Any]:
    lease = _lease(worker)
    assert lease is not None
    assert lease["task"]["kind"] == "analyze"
    _finish(worker, lease, {}, ANALYSIS)
    return lease


def _reviewed(op: TestClient, job_id: str, **choice: Any) -> dict[str, Any]:
    body = {"title": "Pálida Luna", "artist": "Los Suaves", "language": "es", "lyrics": "la la"}
    answer = op.post(f"/api/jobs/{job_id}/confirm", json={**body, **choice})
    assert answer.status_code == 200, answer.text
    return dict(answer.json())


def _upload_ready_to_make(clients: Clients, op: TestClient, **job: Any) -> dict[str, Any]:
    """An upload job whose analysis is done and confirmed: its `make` is ready."""
    created = op.post("/api/jobs", json={"upload": _upload(clients), **job}).json()
    _, analyst = clients.enrol("worker", name=f"analyst-{created['id']}", gpus=[])
    _analyse(analyst)
    return _reviewed(op, created["id"])


def test_an_upload_is_analysed_reviewed_and_becomes_a_song(
    clients: Clients, demo_manifest: str
) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    assert [(t["kind"], t["state"]) for t in job["tasks"]] == [
        ("analyze", "ready"),
        ("make", "waiting"),
    ]
    _, worker = clients.enrol("worker")
    _analyse(worker)
    review = op.get(f"/api/jobs/{job['id']}").json()
    assert review["state"] == "review"
    assert review["tasks"][1]["state"] == "held"
    assert review["tasks"][0]["data"]["best"]["title"] == "Pálida Luna"
    assert _lease(worker) is None, "make waits for the operator"
    confirmed = _reviewed(op, job["id"], title="Pálida luna")
    assert confirmed["state"] == "active"
    assert confirmed["title"] == "Pálida luna"
    lease = _lease(worker, free_vram_mb=4000)
    assert lease is not None
    assert lease["task"]["kind"] == "make"
    params = lease["task"]["params"]
    assert (params["title"], params["artist"], params["language"]) == (
        "Pálida luna",
        "Los Suaves",
        "es",
    )
    assert params["lyrics"] == "la la"
    assert params["lrclib"] is False
    assert lease["task"]["inputs"] == [job["params"]["source"]]
    assert _progress(worker, lease, stage="separate", fraction=0.4, step="voz").json() == {
        "keep_going": True
    }
    running = op.get(f"/api/jobs/{job['id']}").json()["tasks"][1]
    assert (running["state"], running["step"]) == ("running", "voz")
    _finish(worker, lease, {"manifest": demo_manifest})
    done = op.get(f"/api/jobs/{job['id']}").json()
    assert done["state"] == "done"
    assert done["result"]["content_id"] == "demo"
    assert [c["id"] for c in op.get("/api/contents").json()] == ["demo"]
    assert op.get("/api/contents/demo/lyrics").json()["lines"]


def test_a_link_is_fetched_analysed_then_made_on_the_same_worker(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    assert [t["state"] for t in job["tasks"]] == ["ready", "waiting", "waiting"]
    _, offline = clients.enrol("worker", name="offline", internet=False)
    assert _lease(offline) is None, "fetch needs internet"
    _, online = clients.enrol("worker", name="online")
    fetch = _lease(online)
    assert fetch is not None
    assert fetch["task"]["kind"] == "fetch"
    source = clients.services.store.put_bytes(b"downloaded", "audio/mpeg").sha256
    _finish(online, fetch, {"source": source}, {"title": "Pálida Luna (Official)"})
    named = op.get(f"/api/jobs/{job['id']}").json()
    assert named["title"] == "Pálida Luna (Official)", "named by the page, not the link"
    analyse = _lease(online)
    assert analyse is not None
    assert analyse["task"]["kind"] == "analyze"
    assert analyse["task"]["inputs"] == [source]
    _finish(online, analyse, {}, ANALYSIS)
    _reviewed(op, job["id"])
    make = _lease(online)
    assert make is not None
    assert make["task"]["kind"] == "make"
    assert make["task"]["inputs"] == [source], "the analysis adds no blob"
    assert make["task"]["params"]["from"]["fetch"]["source"] == source
    assert make["task"]["params"]["from"]["analyze"]["best"]["artist"] == "Los Suaves"


def test_a_worker_with_its_cpu_slots_full_only_gets_gpu_tasks(clients: Clients) -> None:
    op = clients.operator()
    _upload_ready_to_make(clients, op)
    op.post("/api/jobs", json={"url": "https://example.com/v"})
    _, worker = clients.enrol("worker", name="busy")
    make = _lease(worker, cpu=False)
    assert make is not None
    assert make["task"]["kind"] == "make"
    assert _lease(worker, cpu=False) is None, "fetch needs a CPU slot"
    fetch = _lease(worker)
    assert fetch is not None
    assert fetch["task"]["kind"] == "fetch"


def test_auto_confirm_skips_the_review_only_when_the_analysis_is_sure(clients: Clients) -> None:
    op = clients.operator()
    sure = op.post("/api/jobs", json={"upload": _upload(clients), "auto_confirm": True}).json()
    _, worker = clients.enrol("worker")
    _analyse(worker)
    job = op.get(f"/api/jobs/{sure['id']}").json()
    assert job["state"] == "active"
    make = _lease(worker)
    assert make is not None
    assert make["task"]["params"]["title"] == "Pálida Luna"
    assert make["task"]["params"]["lyrics"] == "la la"
    unsure = op.post("/api/jobs", json={"upload": _upload(clients), "auto_confirm": True}).json()
    lease = _lease(worker)
    assert lease is not None
    _finish(worker, lease, {}, {"best": {"title": "?", "confidence": 0.3}, "lyrics": []})
    assert op.get(f"/api/jobs/{unsure['id']}").json()["state"] == "review"


def test_confirming_without_lyrics_transcribes(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, worker = clients.enrol("worker")
    _analyse(worker)
    assert op.post(f"/api/jobs/{job['id']}/confirm", json={"title": "x"}).status_code == 422
    _reviewed(op, job["id"], lyrics=None)
    make = _lease(worker)
    assert make is not None
    assert make["task"]["params"]["lyrics"] is None
    assert (
        op.post(f"/api/jobs/{job['id']}/confirm", json={"title": "x", "language": "gl"}).status_code
        == 409
    )


def test_a_late_progress_never_brings_a_finished_task_back(
    clients: Clients, services: Services
) -> None:
    """The bug seen on the first real song: a progress call that arrived after `complete`
    made the fetch `running` again, its lease expired and it ran twice."""
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    _, worker = clients.enrol("worker")
    fetch = _lease(worker)
    assert fetch is not None
    source = services.store.put_bytes(b"downloaded", "audio/mpeg").sha256
    _finish(worker, fetch, {"source": source})
    late = _progress(worker, fetch, stage="download", fraction=1.0)
    assert late.json() == {"keep_going": False}
    assert services.queue.expire(now=time.time() + 600) == 0
    task = op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]
    assert (task["state"], task["attempts"], task["error"]) == ("done", 1, None)


def test_a_success_after_a_retry_clears_the_error(clients: Clients, services: Services) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    _, worker = clients.enrol("worker")
    assert _lease(worker) is not None
    assert services.queue.expire(now=time.time() + 600) == 1
    again = _lease(worker)
    assert again is not None
    _finish(worker, again, {"source": services.store.put_bytes(b"x", "audio/mpeg").sha256})
    task = op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]
    assert (task["state"], task["error"], task["error_code"]) == ("done", None, None)


def test_a_cancelled_job_never_becomes_done(clients: Clients, demo_manifest: str) -> None:
    op = clients.operator()
    job = _upload_ready_to_make(clients, op)
    _, worker = clients.enrol("worker")
    lease = _lease(worker)
    assert lease is not None
    op.post(f"/api/jobs/{job['id']}/cancel")
    assert _progress(worker, lease, stage="align").json() == {"keep_going": False}
    late = worker.post(
        f"/api/tasks/{lease['task']['id']}/complete",
        json={"lease_id": lease["lease_id"], "result": {"outputs": {"manifest": demo_manifest}}},
    )
    assert late.status_code == 409
    assert op.get(f"/api/jobs/{job['id']}").json()["state"] == "cancelled"
    assert op.get("/api/contents").json() == []


def test_a_retry_on_a_paused_job_waits_for_resume(clients: Clients, services: Services) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    _, worker = clients.enrol("worker")
    assert _lease(worker) is not None
    op.post(f"/api/jobs/{job['id']}/pause")
    services.queue.expire(now=time.time() + 600)
    assert op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]["state"] == "paused"
    assert _lease(worker) is None
    op.post(f"/api/jobs/{job['id']}/resume")
    assert _lease(worker) is not None


def test_a_broken_finish_fails_the_job_instead_of_leaving_it_active(
    clients: Clients, services: Services
) -> None:
    def broken(job: dict[str, Any]) -> None:
        raise RuntimeError("disk on fire")

    services.queue.on_job_done = broken
    op = clients.operator()
    job = op.post("/api/jobs", json={"kind": "render", "content_id": "x"})
    assert job.status_code == 404  # no such song: nothing was queued
    done = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    _, worker = clients.enrol("worker")
    fetch = _lease(worker)
    assert fetch is not None
    _finish(worker, fetch, {"source": services.store.put_bytes(b"x", "audio/mpeg").sha256})
    analyse = _lease(worker)
    assert analyse is not None
    _finish(worker, analyse, {}, ANALYSIS)
    _reviewed(op, done["id"])
    make = _lease(worker)
    assert make is not None
    _finish(worker, make, {})
    failed = op.get(f"/api/jobs/{done['id']}").json()
    assert (failed["state"], failed["error"]) == ("failed", "disk on fire")


def test_task_logs_are_kept_for_the_live_view(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
    _, worker = clients.enrol("worker")
    fetch = _lease(worker)
    assert fetch is not None
    answer = worker.post(
        f"/api/tasks/{fetch['task']['id']}/log",
        json={
            "lease_id": fetch["lease_id"],
            "log": {"lines": ["[download] 10%", "[download] 20%"]},
        },
    )
    assert answer.status_code == 204
    log = op.get(f"/api/jobs/{job['id']}/tasks/fetch/log")
    assert log.text == "[download] 10%\n[download] 20%"
    whole = clients.services.store.put_bytes(b"the whole log", "text/plain").sha256
    _finish(worker, fetch, {"source": whole, "log": whole})
    assert op.get(f"/api/jobs/{job['id']}/tasks/fetch/log").text == "the whole log"


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
    analyse = services.db.one("SELECT * FROM tasks WHERE id = ?", (f"{job['id']}:analyze",))
    assert services.queue._affinity(analyse, first_id) == 1
    assert services.queue._affinity(analyse, second_id) == 0
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
    task = op.get(f"/api/jobs/{job['id']}").json()["tasks"][0]
    assert (task["attempts"], task["error_code"]) == (2, "worker_lost")


def test_heartbeat_renews_and_tells_to_stop_cancelled_tasks(clients: Clients) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, worker = clients.enrol("worker")
    lease = _lease(worker)
    assert lease is not None
    task = lease["task"]["id"]
    beat = worker.post(
        "/api/worker/heartbeat",
        json={"running": [task], "telemetry": {"gpu_util": 90, "cpu_util": 12, "ram_total_mb": 9}},
    )
    assert beat.json()["stop"] == []
    node = op.get("/api/nodes").json()[0]
    assert (node["telemetry"]["gpu_util"], node["running"]) == (90, [task])
    op.post(f"/api/jobs/{job['id']}/cancel")
    assert worker.post("/api/worker/heartbeat", json={"running": [task]}).json()["stop"] == [task]


def test_capabilities_filter_tasks(clients: Clients) -> None:
    op = clients.operator()
    _upload_ready_to_make(clients, op)
    _, small = clients.enrol("worker", name="small", gpus=[{"name": "GT", "vram_total_mb": 2048}])
    assert _lease(small) is None, "make needs 3.2 GB"
    _, cpu = clients.enrol("worker", name="cpu", gpus=[])
    assert _lease(cpu) is None
    _, big = clients.enrol("worker", name="big", same_host_as_server=True)
    stage = clients.services.stage
    stage.session = stage.session.model_copy(update={"state": "playing"})
    assert _lease(big) is None, "a song plays on that machine"
    stage.session = stage.session.model_copy(update={"state": "paused"})
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
                "failure": {"code": "download_failed", "message": "HTTP 403"},
            },
        )
    failed = op.get(f"/api/jobs/{job['id']}").json()
    assert failed["state"] == "failed"
    assert failed["tasks"][0]["error_code"] == "download_failed"
    assert failed["tasks"][1]["state"] == "cancelled"
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
    _upload_ready_to_make(clients, op)
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


def test_a_confirmed_song_can_go_straight_to_the_queue(
    clients: Clients, demo_manifest: str
) -> None:
    op = clients.operator()
    job = op.post("/api/jobs", json={"upload": _upload(clients)}).json()
    _, worker = clients.enrol("worker")
    _analyse(worker)
    _reviewed(op, job["id"], add_to_queue=True)
    make = _lease(worker)
    assert make is not None
    _finish(worker, make, {"manifest": demo_manifest})
    queue = op.get("/api/stage/queue").json()
    assert [i["content_id"] for i in queue["items"]] == ["demo"]
