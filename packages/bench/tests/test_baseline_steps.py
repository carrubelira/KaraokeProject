from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.audio import duration
from karaoke_bench.baseline.separation import DemucsSeparator
from karaoke_bench.baseline.whisper import FasterWhisperTranscriber

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "fixtures" / "packages" / "demo-sintetico"


def _needs_gpu() -> None:
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("needs a CUDA GPU")


def test_unknown_whisper_model_rejected() -> None:
    with pytest.raises(ValueError, match="tiny-x"):
        FasterWhisperTranscriber(model="tiny-x")


@pytest.mark.models
@pytest.mark.usefixtures("ffmpeg")
def test_demucs_separator_writes_two_stems(tmp_path: Path) -> None:
    _needs_gpu()
    pytest.importorskip("demucs")
    mix = DEMO / "instrumental.wav"
    if not mix.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    separator = DemucsSeparator()
    separator.load()

    stems = separator.separate(mix, tmp_path)

    assert stems.vocals == tmp_path / "vocals.wav"
    assert stems.instrumental == tmp_path / "instrumental.wav"
    assert duration(stems.vocals) == pytest.approx(duration(mix), abs=0.05)
    assert duration(stems.instrumental) == pytest.approx(duration(mix), abs=0.05)


@pytest.mark.models
@pytest.mark.usefixtures("ffmpeg")
def test_demucs_separator_is_deterministic(tmp_path: Path) -> None:
    _needs_gpu()
    pytest.importorskip("demucs")
    mix = DEMO / "instrumental.wav"
    if not mix.is_file():
        pytest.skip("run `uv run karaoke demo fixtures/packages/demo-sintetico` first")
    separator = DemucsSeparator()
    separator.load()

    first = separator.separate(mix, tmp_path / "a")
    second = separator.separate(mix, tmp_path / "b")

    assert first.vocals.read_bytes() == second.vocals.read_bytes()


@pytest.mark.models
@pytest.mark.usefixtures("ffmpeg")
def test_whisper_reports_language(tmp_path: Path) -> None:
    _needs_gpu()
    pytest.importorskip("faster_whisper")
    song = REPO / "bench" / "data" / "jamendo" / "Baila_-_Alfonso_Lugo" / "audio.mp3"
    if not song.is_file():
        pytest.skip("run `uv run karaoke-bench fetch --set jamendo` first")
    from karaoke_bench.audio import cut

    clip = cut(song, 30.0, 45.0, tmp_path / "clip.wav")
    transcriber = FasterWhisperTranscriber(model="small", detect_language=True)
    transcriber.load()

    transcript = transcriber.transcribe(clip, "gl")

    assert transcript.language == "es"
    assert transcript.segments


def test_unknown_qwen_model_rejected() -> None:
    from karaoke_bench.baseline.qwen import QwenTranscriber

    with pytest.raises(ValueError, match="unknown Qwen3-ASR model"):
        QwenTranscriber(model="7b")


@pytest.mark.usefixtures("ffmpeg")
def test_qwen_reads_each_stretch_of_singing_in_the_language_asked(
    tmp_path: Path, make_tone: Callable[..., Path]
) -> None:
    import numpy as np

    pytest.importorskip("torch")  # the transcriber runs under torch.inference_mode
    from karaoke_bench.baseline.qwen import QwenTranscriber
    from karaoke_engine.steps import Transcriber

    class FakeInputs(dict):  # type: ignore[type-arg]
        def to(self, device: object, dtype: object) -> "FakeInputs":
            return self

    class FakeProcessor:
        def __init__(self) -> None:
            self.asked: list[tuple[float, str]] = []

        def apply_transcription_request(self, audio: np.ndarray, language: str) -> FakeInputs:
            self.asked.append((len(audio) / 16000, language))
            return FakeInputs(input_ids=np.zeros((1, 3), dtype=np.int64))

        def decode(self, ids: np.ndarray, return_format: str) -> list[str]:
            assert return_format == "transcription_only"
            return [" ola mar "]

    class FakeNet:
        device, dtype = "cpu", "float32"

        def generate(self, **options: object) -> np.ndarray:
            return np.zeros((1, 8), dtype=np.int64)

    transcriber = QwenTranscriber()
    transcriber._processor, transcriber._net = FakeProcessor(), FakeNet()
    assert isinstance(transcriber, Transcriber)

    transcript = transcriber.transcribe(make_tone("vocals.wav", 6.0), "es")

    # A steady tone is one stretch of singing: one question, in the language given.
    assert transcript.language == "es"
    assert [s.text for s in transcript.segments] == ["ola mar"]
    assert [language for _, language in transcriber._processor.asked] == ["es"]
