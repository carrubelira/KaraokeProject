"""The stage (decision 011): the session, kp-audio's and the screens' sockets, the operator's
start, the end of a song, and what screens may download."""

import dataclasses
import json
import sqlite3
import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from karaoke_server.clock import now_us
from karaoke_server.config import Settings
from karaoke_server.db import MIGRATIONS, Database

from .conftest import Clients

HELLO = {"screen_id": "sala-tv", "width": 1920, "height": 1080, "codecs": ["h264"]}


def _items(**first: Any) -> list[dict[str, Any]]:
    base = {"manifest": None, "start": None, "end": None, "semitones": 0, "singer": None}
    return [
        {**base, "id": "a", "content_id": "demo", "start": 2.0, "semitones": -2, **first},
        {**base, "id": "b", "content_id": "demo"},
    ]


class Stage:
    """One client, started: every request and socket runs on one event loop, as in the server
    (the stage's timers and writers live on it)."""

    def __init__(self, clients: Clients) -> None:
        self.clients = clients
        self.services = clients.services
        self.http = TestClient(
            clients.app, headers={"Authorization": f"Bearer {clients.operator_token}"}
        )

    def operator(self) -> TestClient:
        return self.http

    def client(self) -> TestClient:
        return self.http


@pytest.fixture
def stage(clients: Clients) -> Iterator[Stage]:
    made = Stage(clients)
    with made.http:
        yield made


@pytest.fixture
def queued(stage: Stage, demo_manifest: str) -> Stage:
    """The demo song twice in the queue."""
    stage.services.library.register(demo_manifest)
    op = stage.operator()
    queue = op.get("/api/stage/queue").json()
    op.put("/api/stage/queue", json={**queue, "items": _items()})
    return stage


def _screen(clients: Stage):  # type: ignore[no-untyped-def]
    return clients.http.websocket_connect("/api/screens/ws")


def _hello(ws: Any, **hello: Any) -> dict[str, Any]:
    """Says hello; returns the session it gets after the time and its settings."""
    ws.send_json({"type": "hello", "hello": {**HELLO, **hello}})
    assert ws.receive_json()["type"] == "time"
    assert ws.receive_json()["type"] == "config"
    session = ws.receive_json()
    assert session["type"] == "session"
    return dict(session["session"])


def _closed_after_hello(clients: Stage, hello: dict[str, Any]) -> int:
    """The code the server closes a screen's socket with, right after its hello."""
    with _screen(clients) as ws:
        ws.send_json({"type": "hello", "hello": hello})
        try:
            ws.receive_json()
        except WebSocketDisconnect as closed:
            return closed.code
    raise AssertionError("the socket stayed open")


def _audio(clients: Stage, token: str = "audio-test"):  # type: ignore[no-untyped-def]  # noqa: S107
    return clients.http.websocket_connect(
        "/api/audio/ws", headers={"Authorization": f"Bearer {token}"}
    )


def _audio_ready(ws: Any, epoch: int) -> None:
    ws.send_json({"type": "status", "status": {"state": "ready", "epoch": epoch, "ready": True}})


def _until(ws: Any, state: str) -> dict[str, Any]:
    """Reads sessions until one in `state`."""
    for _ in range(20):
        message = ws.receive_json()
        if message["type"] == "session" and message["session"]["state"] == state:
            return dict(message["session"])
    raise AssertionError(f"no session in {state}")


def _order(clients: Stage, command: str, **body: Any) -> Any:
    return clients.operator().post("/api/stage/commands", json={"command": command, **body})


def test_a_screen_says_hello_and_is_kept(stage: Stage) -> None:
    clients = stage
    with _screen(clients) as ws:
        session = _hello(ws)
        assert (session["state"], session["current"]) == ("idle", None)
        ws.send_json({"type": "time-request", "sent": 123})
        answer = ws.receive_json()
        assert answer["sent"] == 123
        assert abs(answer["now"] - now_us()) < 5_000_000
        status = {"state": "idle", "flags": ["fullscreen"], "sync": {"rtt_ms": 1.5}}
        ws.send_json({"type": "status", "status": status})
        ws.send_json({"type": "time-request", "sent": 1})
        ws.receive_json()  # answered after the status was taken in
        screens = clients.operator().get("/api/stage").json()["screens"]
        assert [(s["id"], s["online"], s["status"]["flags"]) for s in screens] == [
            ("sala-tv", True, ["fullscreen"])
        ]
        # Two tabs of one browser: the second gets told to make up another id.
        assert _closed_after_hello(clients, HELLO) == 4009
    screens = clients.operator().get("/api/stage").json()["screens"]
    assert screens[0]["online"] is False


def test_a_screen_that_does_not_say_hello_is_closed(stage: Stage) -> None:
    clients = stage
    assert _closed_after_hello(clients, {"screen_id": "../etc"}) == 4400


def test_only_the_servers_own_kp_audio_gets_in(stage: Stage) -> None:
    clients = stage
    with pytest.raises(WebSocketDisconnect) as closed, _audio(clients, "wrong") as ws:
        ws.receive_json()
    assert closed.value.code == 4401
    with _audio(clients) as ws:
        assert [ws.receive_json()["type"] for _ in range(3)] == ["time", "config", "session"]
        assert clients.operator().get("/api/stage").json()["audio"]["online"] is True
    assert clients.operator().get("/api/stage").json()["audio"]["online"] is False


def test_nothing_plays_until_the_operator_starts_it(queued: Stage) -> None:
    clients = queued
    with _audio(clients) as audio, _screen(clients) as screen:
        for _ in range(3):
            audio.receive_json()
        _hello(screen)
        screen.send_json({"type": "status", "status": {"state": "idle"}})

        cued = _order(clients, "cue").json()
        assert (cued["state"], cued["epoch"]) == ("cueing", 1)
        assert cued["current"]["item"]["id"] == "a"
        assert cued["anchor"] == {"position": 2.0, "instant": cued["anchor"]["instant"], "rate": 0}
        assert cued["semitones"] == -2
        assert [p["item"]["id"] for p in cued["upcoming"]] == ["b"]
        assert _until(screen, "cueing")["epoch"] == 1
        # Not cued until kp-audio has the song ready, for this epoch.
        assert _order(clients, "start").json()["code"] == "not_cued"
        _audio_ready(audio, epoch=0)
        _audio_ready(audio, epoch=1)
        assert _until(screen, "cued")["epoch"] == 1

        # The screen has not got there: the operator is asked first.
        refused = _order(clients, "start")
        assert refused.status_code == 409
        assert refused.json() | {"detail": ""} == {
            "code": "screens_not_ready", "detail": "", "screens": ["sala-tv"]
        }  # fmt: skip
        before = now_us()
        started = _order(clients, "start", force=True).json()
        assert started["state"] == "playing"
        assert started["anchor"]["rate"] == 1
        assert started["anchor"]["instant"] >= before + 100_000
        assert started["anchor"]["position"] == 2.0

        paused = _order(clients, "pause").json()
        assert (paused["state"], paused["anchor"]["rate"]) == ("paused", 0)
        assert 2.0 <= paused["anchor"]["position"] < 3.0
        sought = _order(clients, "seek", position=30).json()
        assert (sought["state"], sought["anchor"]["position"]) == ("paused", 30)
        # Once the screen is on the frame again, nobody is missing.
        screen.send_json(
            {"type": "status", "status": {"state": "paused", "epoch": 1, "ready": True}}
        )
        screen.send_json({"type": "time-request", "sent": 1})
        while screen.receive_json()["type"] != "time":
            pass
        assert _order(clients, "start").json()["state"] == "playing"

        assert _order(clients, "pitch", value=40).json()["semitones"] == 12
        nxt = _order(clients, "next").json()
        assert (nxt["state"], nxt["epoch"], nxt["current"]["item"]["id"]) == ("cueing", 2, "b")
        assert _order(clients, "next").json()["code"] == "end_of_queue"
        stopped = _order(clients, "stop").json()
        assert (stopped["state"], stopped["current"]) == ("idle", None)


def test_start_needs_the_audio_engine(queued: Stage) -> None:
    with _audio(queued) as audio:
        for _ in range(3):
            audio.receive_json()
        _order(queued, "cue")
        _audio_ready(audio, epoch=1)
        audio.send_json({"type": "time-request", "sent": 1})
        while audio.receive_json()["type"] != "time":
            pass
    assert _order(queued, "start").json()["code"] == "audio_offline"


def test_a_lost_master_output_pauses_every_screen(queued: Stage) -> None:
    with _audio(queued) as audio:
        for _ in range(3):
            audio.receive_json()
        _order(queued, "cue")
        _audio_ready(audio, epoch=1)
        _until(audio, "cued")
        _order(queued, "start")
        lost = {"code": "master_lost", "device": "hdmi", "message": "the TV went off"}
        audio.send_json({"type": "status", "status": {"state": "paused", "errors": [lost]}})
        assert _until(audio, "paused")["anchor"]["rate"] == 0


@pytest.fixture
def silent(settings: Settings, db: Database) -> Iterator[Stage]:
    """A stage with no audio engine on purpose: it keeps time for the screens alone."""
    from karaoke_server.app import build_services, create_app

    quiet = dataclasses.replace(settings, audio="off", go_lead_seconds=0.05)
    services = build_services(quiet, db=db)
    app = create_app(quiet, services=services)
    made = Stage(Clients(app, services, services.auth.add_operator("T"), []))
    with made.http:
        yield made


def test_the_end_of_a_song_cues_the_next_singer(silent: Stage, demo_manifest: str) -> None:
    clients = silent
    clients.services.library.register(demo_manifest)
    op = clients.operator()
    op.put("/api/stage/queue", json={"version": 0, "items": _items(start=0.0, end=0.3)})
    with _screen(clients) as screen:
        _hello(screen)
        assert _order(clients, "cue").json()["state"] == "cued"  # no audio to wait for
        assert _order(clients, "start", force=True).json()["state"] == "playing"
        ended = _until(screen, "ended")
        assert ended["anchor"] == {
            "position": 0.3,
            "instant": ended["anchor"]["instant"],
            "rate": 0,
        }
        following = _until(screen, "cued")
        assert following["current"]["item"]["id"] == "b"
        assert following["epoch"] == ended["epoch"] + 1


def test_screens_download_only_what_is_on_the_stage(queued: Stage, demo_manifest: str) -> None:
    clients = queued
    anyone = TestClient(clients.clients.app)
    manifest = clients.services.library.manifest(demo_manifest)
    video = manifest.tracks[0].blob.sha256
    assert anyone.get(f"/api/screens/blobs/{demo_manifest}").status_code == 200
    ranged = anyone.get(f"/api/screens/blobs/{video}", headers={"Range": "bytes=0-9"})
    assert (ranged.status_code, len(ranged.content)) == (206, 10)
    other = clients.services.store.put_bytes(b"private", "text/plain").sha256
    assert anyone.get(f"/api/screens/blobs/{other}").status_code == 404
    assert anyone.get(f"/api/blobs/{demo_manifest}").status_code == 401


def test_a_screens_settings_reach_it(stage: Stage) -> None:
    clients = stage
    op = clients.operator()
    config = {"name": "Tele", "layout": "lyrics", "theme": "moderno", "display_ms": 35,
              "video_max_height": 720}  # fmt: skip
    with _screen(clients) as ws:
        _hello(ws)
        assert op.put("/api/screens/sala-tv/config", json=config).status_code == 200
        pushed = ws.receive_json()
        assert (pushed["type"], pushed["config"]["layout"]) == ("config", "lyrics")
        assert op.delete("/api/screens/sala-tv").status_code == 409
    with _screen(clients) as ws:
        ws.send_json({"type": "hello", "hello": HELLO})
        ws.receive_json()
        assert ws.receive_json()["config"]["name"] == "Tele"  # kept by its id
    assert op.delete("/api/screens/sala-tv").status_code == 204
    assert op.put("/api/screens/sala-tv/config", json=config).status_code == 404


def test_editing_the_queue_refreshes_what_comes_next(queued: Stage) -> None:
    clients = queued
    with _audio(clients) as audio:
        for _ in range(3):
            audio.receive_json()
        _order(clients, "cue")
        _until(audio, "cueing")
        op = clients.operator()
        op.post("/api/stage/queue/items", json={"items": [{"content_id": "demo"}]})
        session = audio.receive_json()["session"]
        assert [p["item"]["id"] for p in session["upcoming"]][:1] == ["b"]
        assert len(session["upcoming"]) == 2


def test_the_console_snapshot_shows_the_stage(stage: Stage) -> None:
    clients = stage
    with stage.http.websocket_connect("/api/events") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["session"]["state"] == "idle"
        assert snapshot["queue"] == {"version": 0, "items": []}
        assert snapshot["screens"] == []
        assert snapshot["audio"]["online"] is False
        with _screen(clients) as screen:
            _hello(screen)
            event = ws.receive_json()
            assert (event["type"], event["screen"]["id"]) == ("screen", "sala-tv")
        ws.send_json({"type": "ping", "sent": 7})
        while (event := ws.receive_json())["type"] != "pong":
            pass
        assert event["sent"] == 7


def test_the_clock_is_monotonic() -> None:
    first = now_us()
    time.sleep(0.01)
    assert now_us() - first >= 9_000
    assert abs(now_us() - time.perf_counter_ns() // 1000) < 1_000


def test_a_players_queue_and_routing_become_the_stages(tmp_path: Any) -> None:
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    for script in MIGRATIONS[:2]:
        conn.executescript(script)
    conn.execute("PRAGMA user_version = 2")
    config = {"routing": {"master": "hdmi", "routes": [], "screens": [], "policies": {}},
              "calibration": {"audio_ms": {"hdmi": 38.0}, "display_ms": {"tv": 20}}}  # fmt: skip
    conn.execute(
        "INSERT INTO nodes (id, kind, name, credential_hash, capabilities, config, created_at,"
        " last_seen) VALUES ('p_1', 'player', 'sala', 'h', '{}', ?, 'now', 1)",
        (json.dumps(config),),
    )
    items = json.dumps(_items())
    conn.execute(
        "INSERT INTO queues (player_id, version, items, updated_at) VALUES ('p_1', 7, ?, 'now')",
        (items,),
    )
    conn.commit()
    conn.close()
    db = Database(path)
    db.migrate()
    row = db.one("SELECT version, items FROM queue")
    assert row is not None
    assert (row["version"], json.loads(row["items"])[0]["id"]) == (7, "a")
    audio = db.one("SELECT value FROM stage_settings WHERE key = 'audio'")
    assert audio is not None
    assert json.loads(audio["value"]) == {
        "routing": {"master": "hdmi", "routes": [], "policies": {}},
        "calibration_ms": {"hdmi": 38.0},
    }
    assert db.query("SELECT * FROM nodes") == []
