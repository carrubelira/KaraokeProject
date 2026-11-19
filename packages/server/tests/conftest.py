import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karaoke_contracts.nodes import Capabilities, Enrollment, Gpu
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.services import Services

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "fixtures" / "packages" / "demo-sintetico"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings.from_env(
        data_dir=tmp_path / "data", web_dir=tmp_path / "web", tls=False, lease_wait_seconds=0.0
    )
    s.ensure_dirs()
    return s


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.migrate()
    return database


@pytest.fixture
def services(settings: Settings, db: Database) -> Services:
    from karaoke_server.app import build_services

    return build_services(settings, db=db, fingerprint="f" * 64)


@pytest.fixture
def app(settings: Settings, services: Services) -> FastAPI:
    from karaoke_server.app import create_app

    return create_app(settings, services=services)


@dataclass
class Clients:
    app: FastAPI
    services: Services
    operator_token: str
    _opened: list[TestClient]

    def client(self, token: str | None = None) -> TestClient:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        made = TestClient(self.app, headers=headers)
        self._opened.append(made)
        return made

    def operator(self) -> TestClient:
        return self.client(self.operator_token)

    def enrol(
        self, kind: str = "worker", name: str | None = None, **caps: object
    ) -> tuple[str, TestClient]:
        token = self.services.auth.new_enrollment(kind)  # type: ignore[arg-type]
        defaults: dict[str, object] = {"os": "linux"}
        if kind == "worker":
            defaults |= {"gpus": [Gpu(name="RTX 3050", vram_total_mb=4096)], "internet": True}
        capabilities = Capabilities.model_validate({**defaults, **caps})
        body = Enrollment(token=token, kind=kind, name=name or kind, capabilities=capabilities)  # type: ignore[arg-type]
        answer = self.client().post("/api/nodes/enroll", json=body.model_dump(mode="json"))
        assert answer.status_code == 200, answer.text
        data = answer.json()
        return data["node_id"], self.client(data["credential"])


@pytest.fixture
def clients(app: FastAPI, services: Services) -> Iterator[Clients]:
    made = Clients(app, services, services.auth.add_operator("Test"), [])
    yield made
    for client in made._opened:
        client.close()


@pytest.fixture
def demo_manifest(services: Services, tmp_path: Path) -> str:
    """A real manifest of the synthetic demo in the server's store; returns its hash."""
    from karaoke_engine.demo import synthesize_package_audio
    from karaoke_engine.package import build_manifest

    package = tmp_path / "demo"
    shutil.copytree(DEMO, package)
    synthesize_package_audio(package)
    _, blob = build_manifest(package, services.store, content_id="demo")
    return blob.sha256
