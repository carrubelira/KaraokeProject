"""A worker's settings, including those written by earlier versions."""

import json
from pathlib import Path

from karaoke_worker.config import WorkerConfig


def test_settings_from_before_decision_011_still_load(tmp_path: Path) -> None:
    old = {
        "server": "https://localhost:8765",
        "node_id": "w_1",
        "credential": "node_x",
        "fingerprint": "ab" * 32,
        "name": "equipo-gpu",
        "tasks": ["fetch", "make", "render"],
        "player_lock": None,
    }
    (tmp_path / "worker.json").write_text(json.dumps(old), encoding="utf-8")
    config = WorkerConfig.load(tmp_path)
    assert config.server == "http://localhost:8765"
    assert config.same_host is False
    config.same_host = True
    config.save(tmp_path)
    assert WorkerConfig.load(tmp_path).same_host is True
