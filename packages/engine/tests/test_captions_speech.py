import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import (
    DEFAULT_SPEECH_MODEL,
    HALLUCINATIONS,
    transcribe_speech,
    transcribe_speech_in_child,
)

RATE = 16000


@dataclass
class FakeWord:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str
    words: list[FakeWord] = field(default_factory=list)


@dataclass
class FakeInfo:
    language: str


class FakeWhisper:
    def __init__(self, segments: list[FakeSegment]) -> None:
        self.segments = segments
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio: np.ndarray, **options: object) -> tuple[object, FakeInfo]:
        self.calls.append(options)
        return iter(self.segments), FakeInfo("gl")


def said(start: float, text: str, probability: float = 0.9) -> FakeSegment:
    """A segment whose words last 0.3 s each with 0.1 s between them, as Whisper spaces them."""
    words = [
        FakeWord(f" {w}", round(start + i * 0.4, 3), round(start + i * 0.4 + 0.3, 3), probability)
        for i, w in enumerate(text.split())
    ]
    return FakeSegment(start, words[-1].end, f" {text}", words)


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(np.zeros(20 * RATE, dtype="<i2").tobytes())
    return path


def run(audio: Path, segments: list[FakeSegment], speech: list[tuple[float, float]]):  # type: ignore[no-untyped-def]
    whisper = FakeWhisper(segments)
    return transcribe_speech(audio, "gl", whisper=whisper, speech=speech), whisper


@pytest.mark.usefixtures("ffmpeg")
def test_words_keep_their_times_probability_and_punctuation(audio: Path) -> None:
    out, _ = run(audio, [said(1.0, "Nacín aquí, na rúa.", 0.8)], [(0.9, 3.0)])
    assert out.words == (
        TimedWord("Nacín", 1.0, 1.3, 0.8),
        TimedWord("aquí,", 1.4, 1.7, 0.8),
        TimedWord("na", 1.8, 2.1, 0.8),
        TimedWord("rúa.", 2.2, 2.5, 0.8),
    )
    assert out.speech == ((0.9, 3.0),)
    assert out.dropped == ()


@pytest.mark.usefixtures("ffmpeg")
def test_whisper_is_asked_for_word_times_in_the_given_language(audio: Path) -> None:
    _, whisper = run(audio, [said(1.0, "Ola")], [(0.9, 2.0)])
    [options] = whisper.calls
    assert options["language"] == "gl"
    assert options["word_timestamps"] is True
    assert options["vad_filter"] is True
    assert options["condition_on_previous_text"] is False


@pytest.mark.parametrize(
    "text",
    [
        "Subtítulos realizados por la comunidad de Amara.org",
        "Gracias por ver el vídeo.",
        "Grazas por ver.",
        "¡Suscríbete al canal!",
        "Thanks for watching!",
    ],
)
@pytest.mark.usefixtures("ffmpeg")
def test_known_hallucinations_are_dropped(audio: Path, text: str) -> None:
    out, _ = run(audio, [said(1.0, "Nacín aquí."), said(5.0, text)], [(0.9, 2.5), (4.9, 9.0)])
    assert [w.text for w in out.words] == ["Nacín", "aquí."]
    assert [d[2] for d in out.dropped] == [text]
    assert any(p.search(text) for p in HALLUCINATIONS)


@pytest.mark.usefixtures("ffmpeg")
def test_text_where_vad_hears_no_speech_is_dropped(audio: Path) -> None:
    out, _ = run(
        audio, [said(1.0, "Nacín aquí."), said(10.0, "Moitas grazas a todos")], [(0.9, 2.5)]
    )
    assert [w.text for w in out.words] == ["Nacín", "aquí."]
    assert out.dropped == ((10.0, 11.5, "Moitas grazas a todos"),)


@pytest.mark.usefixtures("ffmpeg")
def test_loops_are_dropped_and_reported(audio: Path) -> None:
    loop = said(3.0, " ".join(["si"] * 12))
    again = [said(1.0, "Era o mar."), said(2.0, "Era o mar."), said(2.5, "Era o mar.")]
    out, _ = run(audio, [*again, loop], [(0.0, 20.0)])
    assert " ".join(w.text for w in out.words) == "Era o mar. Era o mar."
    assert len(out.dropped) == 2


def test_default_speech_model_for_galician() -> None:
    assert DEFAULT_SPEECH_MODEL["gl"] == "hitz-large-v3-gl"


def test_child_crash_is_a_memory_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The child process imports the stand-in by name, as it would the real worker.
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    import child_crash

    with pytest.raises(MemoryError, match="out of memory"):
        transcribe_speech_in_child(tmp_path / "audio.flac", "gl", work=child_crash.die)


@pytest.mark.usefixtures("ffmpeg")
def test_punctuation_whisper_glues_to_the_next_word_goes_back(audio: Path) -> None:
    segment = FakeSegment(
        1.0,
        2.5,
        " Que foi .E o mar",
        [
            FakeWord(" Que", 1.0, 1.2, 0.9),
            FakeWord(" foi", 1.3, 1.6, 0.9),
            FakeWord(" .E", 1.7, 1.8, 0.9),
            FakeWord(" o", 1.9, 2.0, 0.9),
            FakeWord(" mar", 2.1, 2.5, 0.9),
        ],
    )
    out, _ = run(audio, [segment], [(0.9, 3.0)])
    assert [w.text for w in out.words] == ["Que", "foi.", "E", "o", "mar"]


@pytest.mark.usefixtures("ffmpeg")
def test_a_word_that_is_only_punctuation_joins_the_previous_one(audio: Path) -> None:
    segment = FakeSegment(
        1.0, 2.0, " Si ...", [FakeWord(" Si", 1.0, 1.3, 0.9), FakeWord(" ...", 1.3, 1.4, 0.9)]
    )
    out, _ = run(audio, [segment], [(0.9, 3.0)])
    assert [w.text for w in out.words] == ["Si..."]


class ChunkWhisper(FakeWhisper):
    """Says one word a second into each piece it gets, and keeps how long each piece was."""

    def __init__(self) -> None:
        super().__init__([])
        self.lengths: list[float] = []

    def transcribe(self, audio: np.ndarray, **options: object) -> tuple[object, FakeInfo]:
        self.lengths.append(len(audio) / RATE)
        return iter([said(1.0, f"Tramo{len(self.lengths)}.")]), FakeInfo("gl")


@pytest.mark.usefixtures("ffmpeg")
def test_long_audio_is_transcribed_in_pieces_cut_in_silences(audio: Path) -> None:
    # 20 s of audio with speech in four stretches; pieces of at most 8 s.
    speech = [(0.5, 3.0), (4.0, 7.0), (9.0, 12.0), (14.0, 18.0)]
    whisper = ChunkWhisper()
    out = transcribe_speech(audio, "gl", whisper=whisper, speech=speech, chunk_seconds=8.0)
    assert len(whisper.lengths) == 3
    assert all(length <= 8.0 for length in whisper.lengths)
    starts = [w.start for w in out.words]
    assert starts == sorted(starts)
    assert len(starts) == 3
    assert starts[0] == pytest.approx(1.0)
    assert all(any(a <= s <= b for a, b in speech) for s in starts)
