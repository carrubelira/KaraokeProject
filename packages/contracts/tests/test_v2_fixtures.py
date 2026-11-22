"""The v2 examples in fixtures/contracts-v2 validate here and parse in the player (kp-proto)."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from karaoke_contracts import Lyrics, Manifest
from karaoke_contracts.control import PlayerCommand, PlayerConfig, Queue, QueueItem
from karaoke_contracts.nodes import Enrollment, Heartbeat, Lease, PlayerStatus

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "contracts-v2"
MODELS: dict[str, type[BaseModel]] = {
    "manifest": Manifest,
    "lyrics": Lyrics,
    "queue": Queue,
    "player-command": PlayerCommand,
    "player-config": PlayerConfig,
    "player-status": PlayerStatus,
    "lease": Lease,
    "heartbeat": Heartbeat,
    "enrollment": Enrollment,
}


@pytest.mark.parametrize("name", sorted(MODELS))
def test_fixture_round_trips(name: str) -> None:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert MODELS[name].model_validate(data).model_dump(mode="json") == data


def test_unknown_fields_are_refused() -> None:
    data = json.loads((FIXTURES / "queue.json").read_text(encoding="utf-8"))
    data["colour"] = "red"
    with pytest.raises(ValidationError):
        Queue.model_validate(data)


def test_manifest_needs_lyrics_and_instrumental() -> None:
    data = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    data["tracks"] = [t for t in data["tracks"] if t["kind"] != "lyrics"]
    with pytest.raises(ValidationError, match="lyrics"):
        Manifest.model_validate(data)


def test_audio_tracks_carry_audio_info() -> None:
    data = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    for track in data["tracks"]:
        if track["kind"] == "vocals":
            track["audio"] = None
    with pytest.raises(ValidationError, match="audio"):
        Manifest.model_validate(data)


def test_entry_point_before_exit_point() -> None:
    with pytest.raises(ValidationError, match="entry point"):
        QueueItem(id="x", content_id="song", start=10, end=5)
