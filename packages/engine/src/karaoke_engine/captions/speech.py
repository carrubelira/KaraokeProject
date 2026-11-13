"""Speech to words with times: Whisper (Galician models for Galician) over a whole interview.

Unlike a song, an interview is speech with long silences and a second voice far from the
microphone. Where there is speech comes from Silero's voice activity detector (bundled with
faster-whisper), not from the loudness detector built for separated singing, which would drop a
quiet interviewer. Whisper fills silences with stock phrases learnt from subtitled videos
("Subtítulos realizados por la comunidad de Amara.org") and can loop: those segments are dropped
and reported, never shown. Text in a public museum must be what was said.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.transcribe import MIN_VOICE_SHARE, WhisperTranscriber, is_loop

# Chosen with the bench (decision 018); other languages use large-v3-turbo.
DEFAULT_SPEECH_MODEL: dict[str, str] = {"gl": "hitz-large-v3-gl"}
HALLUCINATIONS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"amara\.org",
        r"\b(?:gracias|grazas|obrigad[oa])\s+por\s+(?:ver|vernos|verlo|mirar|a\s+súa\s+atención)",
        r"\bthanks?(?:\s+you)?\s+for\s+watching",
        r"\bs[uo]b?scr[ií]b[ea]",
        r"\bsubt[ií]tul(?:os|ado)\s+(?:realizad|feit|hech|por\b)",
    )
)
_MAX_SAME_IN_A_ROW = 2


@dataclass(frozen=True)
class SpeechTranscript:
    words: tuple[TimedWord, ...]
    speech: tuple[tuple[float, float], ...]  # where the voice detector hears speech
    dropped: tuple[tuple[float, float, str], ...]  # text the guards threw away
    model: str


def transcribe_speech(
    audio: Path,
    language: str,
    *,
    model: str = "auto",
    beam_size: int = 5,
    whisper: Any = None,
    speech: Sequence[tuple[float, float]] | None = None,
) -> SpeechTranscript:
    """Words with times and confidence; `speech` regions are detected unless given."""
    samples = load_mono16k(audio)
    regions = tuple(speech) if speech is not None else speech_regions(samples)
    name = model if model != "auto" else DEFAULT_SPEECH_MODEL.get(language, "large-v3-turbo")
    transcriber = WhisperTranscriber(model=name, whisper=whisper)
    found, _ = transcriber.whisper_for_language(language).transcribe(
        samples,
        language=language,
        beam_size=beam_size,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
    )
    words: list[TimedWord] = []
    dropped: list[tuple[float, float, str]] = []
    kept_texts: list[str] = []
    for segment in found:
        text = " ".join(segment.text.split())
        if not text:
            continue
        repeated = len(kept_texts) >= _MAX_SAME_IN_A_ROW and all(
            t.lower() == text.lower() for t in kept_texts[-_MAX_SAME_IN_A_ROW:]
        )
        made_up = (
            _share(regions, segment.start, segment.end) < MIN_VOICE_SHARE
            or any(p.search(text) for p in HALLUCINATIONS)
            or is_loop(text)
            or repeated
        )
        if made_up:
            dropped.append((round(segment.start, 3), round(segment.end, 3), text))
            continue
        kept_texts.append(text)
        words += [
            TimedWord(w.word.strip(), round(w.start, 3), round(w.end, 3), round(w.probability, 3))
            for w in segment.words or ()
            if w.word.strip()
        ]
    transcriber.unload()
    return SpeechTranscript(
        tuple(words), regions, tuple(dropped), transcriber.model_for_language(language)
    )


def speech_regions(samples: npt.NDArray[np.float32]) -> tuple[tuple[float, float], ...]:
    """Silero's speech regions, in seconds."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    found = get_speech_timestamps(samples, VadOptions(min_silence_duration_ms=300))
    return tuple(
        (round(r["start"] / SAMPLE_RATE, 3), round(r["end"] / SAMPLE_RATE, 3)) for r in found
    )


def transcribe_speech_in_child(
    audio: Path,
    language: str,
    *,
    work: Callable[..., SpeechTranscript] | None = None,
    **options: Any,
) -> SpeechTranscript:
    """transcribe_speech in a fresh process, so the model's memory goes back to the system."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        try:
            task: Callable[..., SpeechTranscript] = work or _transcribe_here
            return pool.submit(task, str(audio), language, **options).result()
        except BrokenProcessPool as exc:
            raise MemoryError(
                "the transcriber process was killed (out of memory?): close other programs "
                "and try again"
            ) from exc


def _transcribe_here(audio: str, language: str, **options: Any) -> SpeechTranscript:
    return transcribe_speech(Path(audio), language, **options)


def _share(regions: Sequence[tuple[float, float]], start: float, end: float) -> float:
    """The part of [start, end] inside the speech regions."""
    if end <= start:
        return 0.0
    inside = sum(max(0.0, min(end, b) - max(start, a)) for a, b in regions)
    return inside / (end - start)
