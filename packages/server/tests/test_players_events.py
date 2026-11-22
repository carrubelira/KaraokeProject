"""Players over their WebSocket, and the control's live events."""

import json

import pytest
from fastapi.testclient import TestClient

from karaoke_server.clock import now_us

from .conftest import Clients


def _player_socket(clients: Clients, token: str):  # type: ignore[no-untyped-def]
    return TestClient(clients.app).websocket_connect(
        "/api/players/ws", headers={"Authorization": f"Bearer {token}"}
    )


def _credential(client: TestClient) -> str:
    return str(client.headers["authorization"]).split()[1]


@pytest.fixture
def ready(clients: Clients, demo_manifest: str) -> tuple[str, TestClient]:
    """A player with two songs in its queue."""
    clients.services.library.register(demo_manifest)
    player_id, player = clients.enrol("player", name="sala")
    op = clients.operator()
    queue = op.get(f"/api/players/{player_id}/queue").json()
    queue["items"] = [
        {"id": "a", "content_id": "demo", "manifest": None, "start": 2.0, "end": None,
         "semitones": -2, "singer": None},
        {"id": "b", "content_id": "demo", "manifest": None, "start": None, "end": None,
         "semitones": 0, "singer": None},
    ]  # fmt: skip
    op.put(f"/api/players/{player_id}/queue", json=queue)
    return player_id, player


def test_player_gets_time_config_queue_and_orders(
    clients: Clients, ready: tuple[str, TestClient]
) -> None:
    player_id, player = ready
    op = clients.operator()
    with _player_socket(clients, _credential(player)) as ws:
        first = ws.receive_json()
        assert first["type"] == "time"
        assert abs(first["now"] - now_us()) < 5_000_000
        assert ws.receive_json()["type"] == "config"
        assert ws.receive_json()["queue"]["items"][0]["id"] == "a"
        config = {
            "routing": {"master": "hdmi", "routes": [], "screens": [], "policies": {}},
            "calibration": {"audio_ms": {}, "display_ms": {}},
        }
        assert op.put(f"/api/players/{player_id}/config", json=config).status_code == 200
        pushed = ws.receive_json()
        assert pushed["type"] == "config"
        assert pushed["config"]["routing"]["master"] == "hdmi"
        added = op.post(
            f"/api/players/{player_id}/queue/items", json={"items": [{"content_id": "demo"}]}
        ).json()
        assert ws.receive_json()["queue"] == added

        before = now_us()
        order = op.post(f"/api/players/{player_id}/commands", json={"command": "next"}).json()
        command = ws.receive_json()["command"]
        assert command == order
        assert command["command"] == "load"
        assert command["item_id"] == "a"
        # The anchor is in the future, at the item's entry point.
        assert command["anchor"]["position"] == 2.0
        assert command["anchor"]["instant"] >= before + 200_000
        nxt = op.post(f"/api/players/{player_id}/commands", json={"command": "next"}).json()
        assert nxt["item_id"] == "b"
        ws.receive_json()
        third = op.post(f"/api/players/{player_id}/commands", json={"command": "next"}).json()
        assert third["item_id"] == added["items"][2]["id"]
        ws.receive_json()
        assert (
            op.post(f"/api/players/{player_id}/commands", json={"command": "next"}).status_code
            == 409
        )
        pause = op.post(f"/api/players/{player_id}/commands", json={"command": "pause"}).json()
        assert pause["anchor"]["rate"] == 0.0
        ws.receive_json()
        pitch = op.post(
            f"/api/players/{player_id}/commands", json={"command": "pitch", "value": 40}
        ).json()
        assert pitch["value"] == 12.0
        assert ws.receive_json()["command"]["command"] == "pitch"

        ws.send_text(json.dumps({"type": "time-request", "sent": 123}))
        assert ws.receive_json()["sent"] == 123
        status = {
            "type": "status",
            "status": {
                "state": "playing",
                "position": 3.5,
                "semitones": -2,
                "errors": [{"code": "output_lost", "device": "wasapi:tv", "message": "gone"}],
            },
        }
        ws.send_text(json.dumps(status))
        # Answered after the status was taken in.
        ws.send_text(json.dumps({"type": "time-request", "sent": 1}))
        assert ws.receive_json()["sent"] == 1
    players = op.get("/api/players").json()
    assert players[0]["status"]["position"] == 3.5
    assert players[0]["status"]["errors"][0]["code"] == "output_lost"
    assert players[0]["online"] is False


def test_orders_to_an_offline_player_are_refused(
    clients: Clients, ready: tuple[str, TestClient]
) -> None:
    player_id, _ = ready
    answer = clients.operator().post(f"/api/players/{player_id}/commands", json={"command": "stop"})
    assert answer.status_code == 409


def test_sockets_need_the_right_identity(clients: Clients) -> None:
    from starlette.websockets import WebSocketDisconnect

    _, worker = clients.enrol("worker")
    with pytest.raises(WebSocketDisconnect), _player_socket(clients, _credential(worker)) as ws:
        ws.receive_json()
    with (
        pytest.raises(WebSocketDisconnect),
        TestClient(clients.app).websocket_connect("/api/events") as ws,
    ):
        ws.receive_json()


def test_control_gets_a_snapshot_then_live_events(clients: Clients) -> None:
    op = clients.operator()
    with TestClient(clients.app).websocket_connect(
        "/api/events", headers={"Authorization": f"Bearer {clients.operator_token}"}
    ) as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["jobs"] == []
        assert snapshot["players"] == []
        assert snapshot["nodes"] == []
        player_id, _ = clients.enrol("player", name="sala")
        event = ws.receive_json()
        assert (event["type"], event["node"]["id"]) == ("node", player_id)
        job = op.post("/api/jobs", json={"url": "https://example.com/v"}).json()
        event = ws.receive_json()
        assert (event["type"], event["job"]["id"]) == ("job", job["id"])
        ws.send_json({"type": "ping", "sent": 7})
        assert ws.receive_json()["sent"] == 7


def test_a_reconnected_player_is_trusted_for_what_it_has_on(
    clients: Clients, ready: tuple[str, TestClient]
) -> None:
    player_id, player = ready
    op = clients.operator()
    with _player_socket(clients, _credential(player)) as ws:
        for _ in range(3):
            ws.receive_json()  # time, config, queue
        op.post(f"/api/players/{player_id}/commands", json={"command": "load", "item_id": "a"})
        ws.receive_json()
    # It restarts with nothing on: "play" now asks for the song again.
    with _player_socket(clients, _credential(player)) as ws:
        for _ in range(3):
            ws.receive_json()
        ws.send_text(json.dumps({"type": "status", "status": {"state": "idle"}}))
        ws.send_text(json.dumps({"type": "time-request", "sent": 1}))
        ws.receive_json()
        answer = op.post(
            f"/api/players/{player_id}/commands", json={"command": "play", "item_id": "a"}
        )
        assert answer.json()["command"] == "load"
        ws.receive_json()
    # It reconnects with the song still on: plain "play" plays it.
    with _player_socket(clients, _credential(player)) as ws:
        for _ in range(3):
            ws.receive_json()
        ws.send_text(json.dumps({"type": "status", "status": {"state": "paused", "item_id": "b"}}))
        ws.send_text(json.dumps({"type": "time-request", "sent": 1}))
        ws.receive_json()
        played = op.post(f"/api/players/{player_id}/commands", json={"command": "play"}).json()
        assert (played["command"], played["item_id"]) == ("play", "b")
