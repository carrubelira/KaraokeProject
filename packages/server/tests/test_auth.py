from karaoke_contracts.nodes import Capabilities, Enrollment
from karaoke_server.auth import COOKIE

from .conftest import Clients


def test_operator_signs_in_with_token_and_gets_a_cookie(clients: Clients) -> None:
    anonymous = clients.client()
    assert anonymous.get("/api/jobs").status_code == 401
    answer = anonymous.post("/api/session", json={"token": clients.operator_token})
    assert answer.status_code == 200
    assert answer.json()["name"] == "Test"
    assert COOKIE in answer.cookies
    assert anonymous.get("/api/jobs").status_code == 200
    assert anonymous.post("/api/session", json={"token": "op_wrong"}).status_code == 401


def test_preferences_are_kept_per_operator(clients: Clients) -> None:
    op = clients.operator()
    prefs = {"shortcuts": {"transport.play": "Space"}, "layout": "directo"}
    assert op.put("/api/session/preferences", json=prefs).status_code == 200
    assert op.get("/api/session").json()["preferences"] == prefs


def test_enrollment_token_works_once(clients: Clients) -> None:
    token = clients.services.auth.new_enrollment("worker")
    body = Enrollment(token=token, kind="worker", name="w", capabilities=Capabilities(os="linux"))
    first = clients.client().post("/api/nodes/enroll", json=body.model_dump(mode="json"))
    assert first.status_code == 200
    assert set(first.json()) == {"node_id", "credential"}
    again = clients.client().post("/api/nodes/enroll", json=body.model_dump(mode="json"))
    assert again.status_code == 403


def test_operators_make_enrollment_tokens_and_revoke_nodes(clients: Clients) -> None:
    op = clients.operator()
    made = op.post("/api/enrollments", json={"kind": "worker"})
    assert made.json()["token"].startswith("enrol_w_")
    node_id, worker = clients.enrol("worker")
    assert worker.get("/api/nodes/me").json()["id"] == node_id
    assert [n["id"] for n in op.get("/api/nodes").json()] == [node_id]
    assert op.delete(f"/api/nodes/{node_id}").status_code == 204
    assert worker.get("/api/nodes/me").status_code == 401


def test_nodes_cannot_use_operator_routes(clients: Clients) -> None:
    _, worker = clients.enrol("worker")
    assert worker.get("/api/jobs").status_code == 401
    assert worker.get("/api/stage").status_code == 401


def test_nodes_update_their_capabilities(clients: Clients) -> None:
    node_id, worker = clients.enrol("worker", gpus=[])
    caps = {
        "os": "windows",
        "gpus": [{"name": "RTX 4070", "vram_total_mb": 12288}],
        "internet": True,
    }
    assert worker.put("/api/nodes/me/capabilities", json=caps).status_code == 200
    listed = clients.operator().get("/api/nodes").json()[0]["capabilities"]
    assert listed["gpus"][0]["name"] == "RTX 4070"
    assert listed["os"] == "windows"
    assert node_id
