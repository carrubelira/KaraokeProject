"""Enrolling over real TLS: the worker pins the server's self-signed certificate."""

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import uvicorn

from karaoke_contracts.nodes import Capabilities, Enrollment
from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_server.tls import ensure_certificate, fingerprint
from karaoke_worker.client import FingerprintMismatchError, ServerClient, enrol


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def tls_server(tmp_path: Path) -> Iterator[tuple[str, str, str]]:
    settings = Settings.from_env(data_dir=tmp_path / "server", web_dir=None)
    cert, key = ensure_certificate(settings.tls_dir)
    pin = fingerprint(cert)
    services = build_services(settings, fingerprint=pin)
    token = services.auth.new_enrollment("worker")
    port = _free_port()
    config = uvicorn.Config(
        create_app(settings, services=services), host="127.0.0.1", port=port, log_level="warning",
        ssl_certfile=str(cert), ssl_keyfile=str(key),
    )  # fmt: skip
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the server did not start"
        time.sleep(0.02)
    try:
        yield f"https://127.0.0.1:{port}", pin, token
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _request(token: str) -> Enrollment:
    return Enrollment(token=token, kind="worker", name="w", capabilities=Capabilities(os="linux"))


def test_enrolment_pins_the_certificate(tmp_path: Path) -> None:
    with tls_server(tmp_path) as (url, pin, token):
        cert = tmp_path / "worker" / "server.crt"
        with pytest.raises(FingerprintMismatchError):
            enrol(url, token, _request(token), cert, "0" * 64)
        enrolled = enrol(url, token, _request(token), cert, pin)
        assert enrolled.server_fingerprint == pin
        client = ServerClient(url, enrolled.credential, cert)
        assert client.json("/api/nodes/me")["id"] == enrolled.node_id
        client.close()
