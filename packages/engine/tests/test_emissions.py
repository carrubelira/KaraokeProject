from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.emissions import Vocab, compact
from karaoke_engine.align.models import (
    DEFAULT_BY_LANGUAGE,
    FALLBACK_MODEL,
    MODELS,
    CtcModelSpec,
)

DEMO = Path(__file__).resolve().parents[3] / "fixtures" / "packages" / "demo-sintetico"
LETTERS = {ch: i + 2 for i, ch in enumerate("abcdeglmnorsxz")}


def _vocab(fallbacks: dict[str, str] | None = None) -> Vocab:
    mapping = {"<pad>": 0, "|": 1, **LETTERS}
    return Vocab.from_mapping(mapping, blank=0, fallbacks=fallbacks or {})


def test_vocab_uses_fallback_before_base_letter() -> None:
    ids = _vocab({"j": "x"}).encode("janela")

    assert ids[0] == LETTERS["x"]
    assert len(ids) == 6


def test_vocab_falls_back_to_the_base_letter() -> None:
    assert _vocab().encode("ç") == (LETTERS["c"],)
    assert _vocab().encode("é") == (LETTERS["e"],)


def test_vocab_drops_what_it_cannot_spell() -> None:
    assert _vocab().encode("ola!'") == (LETTERS["o"], LETTERS["l"], LETTERS["a"])
    assert _vocab().encode("q") == ()


def test_blank_and_delimiter_come_from_the_mapping() -> None:
    vocab = Vocab.from_mapping({"[PAD]": 5, " ": 0, "a": 1}, blank=5, fallbacks={})

    assert vocab.blank == 5
    assert vocab.delimiter == 0


def test_uppercase_vocabularies_are_matched() -> None:
    vocab = Vocab.from_mapping({"<pad>": 0, "|": 1, "A": 2, "B": 3}, blank=0, fallbacks={})

    assert vocab.encode("ab") == (2, 3)


def test_compact_keeps_blank_and_any_columns() -> None:
    lp = np.log(np.array([[0.6, 0.1, 0.3], [0.2, 0.7, 0.1]], dtype=np.float32))

    out = compact(lp, blank=0, ids=[2])

    assert out.shape == (2, 3)
    np.testing.assert_allclose(out[:, 0], lp[:, 0])
    np.testing.assert_allclose(out[:, 1], [np.log(0.3), np.log(0.7)], rtol=1e-6)
    np.testing.assert_allclose(out[:, 2], lp[:, 2])


def test_every_language_has_a_pinned_model() -> None:
    assert {"gl", "es", "pt", "en", "fr", "de"} <= set(DEFAULT_BY_LANGUAGE)
    assert FALLBACK_MODEL in MODELS
    for spec in MODELS.values():
        assert len(spec.revision) == 40


@pytest.mark.models
@pytest.mark.usefixtures("ffmpeg")
def test_emissions_cover_the_audio() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")
    vocals = DEMO / "vocals.wav"
    if not vocals.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    from karaoke_engine.align.audio import load_mono16k
    from karaoke_engine.align.emissions import EmissionModel

    samples = load_mono16k(vocals)
    model = EmissionModel(MODELS["nos-xlsr-300m-gl"])
    model.load()
    ids = model.vocab.encode("ola")

    emissions = model.emissions(samples, ids)

    seconds = emissions.log_probs.shape[0] * emissions.frame_seconds
    assert seconds == pytest.approx(len(samples) / 16000, abs=0.05)
    assert emissions.log_probs.shape[1] == 2 + len(ids)


def test_compact_tensor_matches_compact() -> None:
    torch = pytest.importorskip("torch")
    from karaoke_engine.align.emissions import compact_tensor

    rng = np.random.default_rng(0)
    logits = torch.from_numpy(rng.normal(size=(50, 12)).astype(np.float32))
    log_probs = logits.log_softmax(dim=-1)

    out = compact_tensor(log_probs, blank=3, ids=[5, 0, 11])

    np.testing.assert_allclose(out, compact(log_probs.numpy(), blank=3, ids=[5, 0, 11]), rtol=1e-6)


def test_unload_drops_the_model_and_features() -> None:
    from karaoke_engine.align.emissions import EmissionModel

    model = EmissionModel(MODELS["nos-xlsr-300m-gl"])
    model._net, model._features = object(), object()

    model.unload()

    assert model._net is None
    assert model._features is None


def _big_spec() -> CtcModelSpec:
    return CtcModelSpec("someone/big-model", "a" * 40, "MIT", half=True)


def test_a_big_model_is_halved_once_in_its_own_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from karaoke_engine.align import emissions

    ran: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        ran.append(command)
        Path(command[-1]).mkdir(parents=True)
        (Path(command[-1]) / "model.safetensors").write_bytes(b"x")

    monkeypatch.setattr(emissions, "CACHE", tmp_path)
    monkeypatch.setattr(subprocess, "run", fake_run)

    target = emissions.half_copy(_big_spec())

    assert (target / "model.safetensors").is_file()
    assert ran[0][1:5] == ["-m", "karaoke_engine.align.emissions", "someone/big-model", "a" * 40]
    assert emissions.half_copy(_big_spec()) == target
    assert len(ran) == 1


def test_a_halving_that_dies_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from karaoke_engine.align import emissions

    def failing_run(command: list[str], check: bool) -> None:
        Path(command[-1]).mkdir(parents=True)
        (Path(command[-1]) / "model.safetensors").write_bytes(b"half")
        raise subprocess.CalledProcessError(-9, command)

    monkeypatch.setattr(emissions, "CACHE", tmp_path)
    monkeypatch.setattr(subprocess, "run", failing_run)

    with pytest.raises(RuntimeError, match="16 bits"):
        emissions.half_copy(_big_spec())

    assert not list(tmp_path.rglob("model.safetensors"))


def test_only_models_marked_big_get_a_copy() -> None:
    from karaoke_engine.align.emissions import source_of

    spec = MODELS["nos-xlsr-300m-gl"]

    assert source_of(spec, half=True) == (spec.repo, spec.revision)
    assert MODELS["music-w2vbert-ctc"].half


def test_the_copy_is_only_for_16_bit_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from karaoke_engine.align import emissions

    monkeypatch.setattr(emissions, "CACHE", tmp_path)
    monkeypatch.setattr(emissions, "half_copy", lambda spec: tmp_path / "copy")

    assert emissions.source_of(_big_spec(), half=True) == (str(tmp_path / "copy"), None)
    # On the CPU the model runs in 32 bits, from the repository as it is.
    assert emissions.source_of(_big_spec(), half=False) == ("someone/big-model", "a" * 40)


def test_the_vocabulary_is_read_without_loading_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from karaoke_engine.align import emissions

    files = {
        "vocab.json": json.dumps({"<pad>": 0, "|": 1, "a": 2, "b": 3}),
        "config.json": json.dumps({"pad_token_id": 0}),
    }

    def fake_file(repo: str, name: str, revision: str) -> str:
        path = tmp_path / name
        path.write_text(files[name], encoding="utf-8")
        return str(path)

    monkeypatch.setattr(emissions, "_hub_file", fake_file)
    model = emissions.EmissionModel(MODELS["nos-xlsr-300m-gl"])

    assert model.vocab.encode("ab") == (2, 3)
    assert model.vocab.blank == 0
    assert model._net is None


def test_a_copy_left_without_its_weights_is_made_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from karaoke_engine.align import emissions

    def fake_run(command: list[str], check: bool) -> None:
        Path(command[-1]).mkdir(parents=True)
        (Path(command[-1]) / "model.safetensors").write_bytes(b"x")

    monkeypatch.setattr(emissions, "CACHE", tmp_path)
    monkeypatch.setattr(subprocess, "run", fake_run)
    spec = _big_spec()
    broken = tmp_path / f"someone--big-model-{'a' * 12}-fp16"
    broken.mkdir()
    (broken / "config.json").write_text("{}", encoding="utf-8")

    target = emissions.half_copy(spec)

    assert target == broken
    assert (target / "model.safetensors").is_file()
    assert not (target / "config.json").exists()
