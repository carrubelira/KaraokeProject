import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.emissions import Emissions, Vocab, compact
from karaoke_engine.captions import refine
from karaoke_engine.captions.refine import refine_words
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import SpeechTranscript

RATE = 16000
HOP = 0.02
ALPHABET = "abcdefghijklmnopqrstuvwxyzñáéíóú"

pytestmark = pytest.mark.usefixtures("ffmpeg")


class ScriptedModel:
    """Emissions where each listed letter peaks at its time and the blank wins elsewhere."""

    def __init__(self, peaks: Sequence[tuple[str, float]]) -> None:
        mapping = {"<pad>": 0, "|": 1, **{ch: i + 2 for i, ch in enumerate(ALPHABET)}}
        self.vocab = Vocab.from_mapping(mapping, blank=0, fallbacks={})
        self.peaks = list(peaks)
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def unload(self) -> None:
        pass

    def emissions(self, samples: np.ndarray, ids: Sequence[int]) -> Emissions:
        frames = len(samples) // round(HOP * RATE)
        lp = np.full((frames, len(ALPHABET) + 2), -8.0, dtype=np.float32)
        lp[:, 0] = -0.01
        for ch, seconds in self.peaks:
            frame = round(seconds / HOP)
            lp[frame, :] = -8.0
            lp[frame, self.vocab.ids[ch]] = -0.01
        return Emissions(compact(lp, 0, ids), HOP)


def _audio(tmp_path: Path, seconds: float) -> Path:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(np.zeros(round(seconds * RATE), dtype="<i2").tobytes())
    return path


def _spell(word: str, start: float, step: float = 0.06) -> list[tuple[str, float]]:
    return [(ch, start + i * step) for i, ch in enumerate(word)]


def test_words_move_to_the_aligned_frames(tmp_path: Path) -> None:
    # Whisper put both words 0.4 s early; the letters say where they are.
    peaks = _spell("nacín", 2.0) + _spell("aquí", 2.5)
    words = (TimedWord("Nacín", 1.6, 2.2, 0.9, "A"), TimedWord("aquí.", 2.25, 2.7, 0.8, "A"))
    out = refine_words(
        _audio(tmp_path, 5.0), SpeechTranscript(words, (), (), "m"), model=ScriptedModel(peaks)
    )
    assert out.words[0].start == pytest.approx(2.0, abs=0.04)
    assert out.words[1].start == pytest.approx(2.5, abs=0.04)
    assert out.words[1].end > out.words[1].start
    assert [(w.text, w.confidence, w.speaker) for w in out.words] == [
        ("Nacín", 0.9, "A"),
        ("aquí.", 0.8, "A"),
    ]


def test_a_stretch_that_does_not_align_keeps_whisper_times(tmp_path: Path) -> None:
    # Digits Whisper wrote that the model cannot spell, and nothing in the emissions.
    words = (TimedWord("1978", 1.0, 1.6, 0.9),)
    out = refine_words(
        _audio(tmp_path, 3.0), SpeechTranscript(words, (), (), "m"), model=ScriptedModel([])
    )
    assert out.words == words


def test_a_word_is_never_moved_far(tmp_path: Path) -> None:
    # The letters of the same word are said again 3 s later: it stays near Whisper's time.
    peaks = _spell("mar", 1.1) + _spell("mar", 4.5)
    words = (TimedWord("mar", 1.0, 1.4, 0.9),)
    out = refine_words(
        _audio(tmp_path, 6.0), SpeechTranscript(words, (), (), "m"), model=ScriptedModel(peaks)
    )
    assert out.words[0].start == pytest.approx(1.1, abs=0.04)


def test_an_hour_is_aligned_stretch_by_stretch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sizes: list[int] = []
    real = refine.align_segments

    def spy(log_probs, *args, **kwargs):  # type: ignore[no-untyped-def]
        sizes.append(len(log_probs))
        return real(log_probs, *args, **kwargs)

    monkeypatch.setattr(refine, "align_segments", spy)
    starts = [60.0 * k for k in range(1, 60)]
    peaks = [p for t in starts for p in _spell("si", t)]
    words = tuple(TimedWord("Si.", t - 0.3, t + 0.2, 0.9) for t in starts)
    out = refine_words(
        _audio(tmp_path, 3600.0), SpeechTranscript(words, (), (), "m"), model=ScriptedModel(peaks)
    )
    assert len(sizes) == len(starts)
    assert max(sizes) < 5 / HOP
    assert [w.start for w in out.words] == pytest.approx(starts, abs=0.04)
