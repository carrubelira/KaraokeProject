"""Enrolling against a real server over plain HTTP (decision 011: one LAN, no TLS)."""

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import uvicorn

from karaoke_contracts.nodes import Capabilities, Enrollment
from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_worker.client import ServerClient, enrol


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def http_server(tmp_path: Path) -> Iterator[tuple[str, str]]:
    settings = Settings.from_env(data_dir=tmp_path / "server", web_dir=None, audio="off")
    services = build_services(settings)
    token = services.auth.new_enrollment("worker")
    port = _free_port()
    config = uvicorn.Config(
        create_app(settings, services=services), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the server did not start"
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}", token
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _request(token: str) -> Enrollment:
    return Enrollment(token=token, kind="worker", name="w", capabilities=Capabilities(os="linux"))


def test_a_worker_enrols_and_then_talks_with_its_credential(tmp_path: Path) -> None:
    with http_server(tmp_path) as (url, token):
        enrolled = enrol(url, token, _request(token))
        client = ServerClient(url, enrolled.credential)
        assert client.json("/api/nodes/me")["id"] == enrolled.node_id
        assert client.lease(None, wait=False) is None
        client.close()
