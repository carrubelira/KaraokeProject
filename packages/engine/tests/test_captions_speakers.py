import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speakers import assign_speakers
from karaoke_engine.captions.speech import SpeechTranscript

RATE = 16000


def _audio(tmp_path: Path, voices: Sequence[tuple[float, float, int]], seconds: float) -> Path:
    """Silence with tones where people speak: (start, end, frequency); a voice is a frequency."""
    samples = np.zeros(round(seconds * RATE), dtype=np.float32)
    t = np.arange(len(samples)) / RATE
    for start, end, hz in voices:
        inside = (t >= start) & (t < end)
        samples[inside] += 0.3 * np.sin(2 * np.pi * hz * t[inside])
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def tone_embed(windows: Sequence[npt.NDArray[np.float32]]) -> npt.NDArray[np.float32]:
    """A stand-in voice print: energy below 300 Hz, above it, and how much both sound at once."""
    out = []
    for window in windows:
        spectrum = np.abs(np.fft.rfft(window)) ** 2
        freqs = np.fft.rfftfreq(len(window), 1 / RATE)
        total = spectrum.sum() + 1e-9
        low, high = spectrum[freqs < 300].sum() / total, spectrum[freqs > 300].sum() / total
        out.append([low, high, 2 * min(low, high)])
    return np.asarray(out, dtype=np.float32)


def _words(spans: Sequence[tuple[float, float]]) -> tuple[TimedWord, ...]:
    """A word every 0.5 s inside each span."""
    words = []
    for start, end in spans:
        t = start
        while t + 0.4 <= end:
            words.append(TimedWord("palabra", round(t, 2), round(t + 0.4, 2), 0.9))
            t += 0.5
    return tuple(words)


def _transcript(spans: Sequence[tuple[float, float]]) -> SpeechTranscript:
    return SpeechTranscript(_words(spans), tuple(spans), (), "fake@0")


@pytest.mark.usefixtures("ffmpeg")
def test_two_voices_get_two_labels_and_the_talker_is_a(tmp_path: Path) -> None:
    voices = [(0.0, 10.0, 200), (10.5, 13.0, 400), (13.5, 25.0, 200)]
    audio = _audio(tmp_path, voices, 26.0)
    out = assign_speakers(audio, _transcript([(a, b) for a, b, _ in voices]), embed=tone_embed)
    for word in out.words:
        middle = (word.start + word.end) / 2
        expected = "B" if 10.5 <= middle < 13.0 else "A"
        assert word.speaker == expected, word


@pytest.mark.usefixtures("ffmpeg")
def test_a_monologue_is_all_a(tmp_path: Path) -> None:
    audio = _audio(tmp_path, [(0.0, 12.0, 200), (12.5, 20.0, 210)], 21.0)
    out = assign_speakers(audio, _transcript([(0.0, 12.0), (12.5, 20.0)]), embed=tone_embed)
    assert {w.speaker for w in out.words} == {"A"}


@pytest.mark.usefixtures("ffmpeg")
def test_turns_shorter_than_a_second_are_smoothed(tmp_path: Path) -> None:
    # A 0.6 s blip of another voice inside a long answer, then a real 3 s turn.
    voices = [(0.0, 8.0, 200), (8.0, 8.6, 400), (8.6, 16.0, 200), (16.5, 19.5, 400)]
    audio = _audio(tmp_path, voices, 20.0)
    out = assign_speakers(audio, _transcript([(0.0, 16.0), (16.5, 19.5)]), embed=tone_embed)
    inside = [w.speaker for w in out.words if w.end <= 16.0]
    assert set(inside) == {"A"}
    assert {w.speaker for w in out.words if w.start >= 16.5} == {"B"}


@pytest.mark.usefixtures("ffmpeg")
def test_words_outside_speech_take_the_nearest_label(tmp_path: Path) -> None:
    voices = [(0.0, 10.0, 200), (10.5, 14.0, 400)]
    audio = _audio(tmp_path, voices, 16.0)
    transcript = _transcript([(0.0, 10.0), (10.5, 14.0)])
    stray = TimedWord("eh", 14.6, 14.9, 0.5)
    out = assign_speakers(
        audio,
        SpeechTranscript((*transcript.words, stray), transcript.speech, (), "fake@0"),
        embed=tone_embed,
    )
    assert out.words[-1].speaker == "B"


@pytest.mark.usefixtures("ffmpeg")
def test_where_the_voice_print_cannot_tell_is_reported(tmp_path: Path) -> None:
    # From 18.5 s to 20 s both voices sound at once: the print is as far from one as the other.
    voices = [(0.0, 10.0, 200), (10.5, 18.0, 400), (18.5, 20.0, 200), (18.5, 20.0, 400),
              (20.5, 35.0, 200)]  # fmt: skip
    audio = _audio(tmp_path, voices, 36.0)
    spans = [(0.0, 10.0), (10.5, 18.0), (18.5, 20.0), (20.5, 35.0)]
    out = assign_speakers(audio, _transcript(spans), embed=tone_embed)
    assert out.unsure_speaker
    assert all(18.0 <= t <= 20.5 for t in out.unsure_speaker)


@pytest.mark.usefixtures("ffmpeg")
def test_no_speech_leaves_the_transcript_as_it_was(tmp_path: Path) -> None:
    audio = _audio(tmp_path, [], 5.0)
    transcript = SpeechTranscript((), (), (), "fake@0")
    assert assign_speakers(audio, transcript, embed=tone_embed) == transcript


def _plain_words(count: int) -> tuple[TimedWord, ...]:
    return tuple(TimedWord("palabra", i * 0.5, i * 0.5 + 0.4, 0.9) for i in range(count))


def test_a_blurred_stretch_inside_one_turn_is_not_asked_about() -> None:
    from karaoke_engine.captions.speakers import unsure_changes

    labels = ["A"] * 10
    margins = [0.5, 0.5, 0.5, 0.02, 0.03, 0.5, 0.5, 0.5, 0.5, 0.5]
    assert unsure_changes(_plain_words(10), labels, margins) == ()


def test_a_blurred_change_of_turn_is_asked_about() -> None:
    from karaoke_engine.captions.speakers import unsure_changes

    labels = ["A"] * 4 + ["B"] * 6
    margins = [0.5, 0.5, 0.5, 0.02, 0.03, 0.5, 0.5, 0.5, 0.5, 0.5]
    assert unsure_changes(_plain_words(10), labels, margins) == (1.5,)
