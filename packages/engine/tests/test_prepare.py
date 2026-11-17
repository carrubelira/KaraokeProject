from pathlib import Path

import pytest

from karaoke_engine import make
from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, DEFAULT_SECOND, FALLBACK_MODEL, MODELS
from karaoke_engine.steps import Stems


class _FakeSeparator:
    name = "fake"

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def load(self) -> None:
        self.calls.append("separator.load")

    def unload(self) -> None:
        self.calls.append("separator.unload")

    def separate(self, mix: Path, out_dir: Path) -> Stems:
        raise AssertionError("preparing must not separate anything")


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(make, "default_separator", lambda: _FakeSeparator(seen))
    monkeypatch.setattr(
        make, "_download", lambda repo, revision: seen.append(f"download {repo}@{revision}")
    )
    monkeypatch.setattr(make, "half_copy", lambda spec: seen.append(f"halve {spec.repo}"))
    monkeypatch.setattr(
        make.WhisperTranscriber,
        "prepare_for",
        lambda self, language: seen.append(f"asr {language}"),
    )
    return seen


def test_prepare_models_fetches_every_model_of_a_language_one_at_a_time(calls: list[str]) -> None:
    notes: list[str] = []
    make.prepare_models("gl", note=notes.append)
    spec = MODELS[DEFAULT_BY_LANGUAGE["gl"]]
    music = MODELS[DEFAULT_SECOND or ""]
    assert calls == [
        "separator.load",
        "separator.unload",
        f"download {spec.repo}@{spec.revision}",
        f"download {music.repo}@{music.revision}",
        f"halve {music.repo}",
        "asr gl",
    ]
    assert notes == ["separator", "aligner", "transcriber"]


def test_prepare_models_uses_the_fallback_aligner_for_other_languages(calls: list[str]) -> None:
    make.prepare_models("eu")
    spec = MODELS[FALLBACK_MODEL]
    assert f"download {spec.repo}@{spec.revision}" in calls


def test_prepare_models_stores_a_big_aligner_in_16_bits(calls: list[str]) -> None:
    make.prepare_models("eu")
    spec = MODELS[FALLBACK_MODEL]
    assert spec.half
    # Right after its download and before the transcriber: the copy needs the memory to itself.
    at = calls.index(f"download {spec.repo}@{spec.revision}")
    assert calls[at + 1] == f"halve {spec.repo}"
    assert calls[-1] == "asr eu"
