"""Speech to words with times: Whisper (Galician models for Galician) over a whole interview.

Unlike a song, an interview is speech with long silences and a second voice far from the
microphone. Where there is speech comes from Silero's voice activity detector (bundled with
faster-whisper), not from the loudness detector built for separated singing, which would drop a
quiet interviewer. Whisper fills silences with stock phrases learnt from subtitled videos
("Subtítulos realizados por la comunidad de Amara.org") and can loop: those segments are dropped
and reported, never shown. Text in a public museum must be what was said.
"""

import itertools
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
# Longest piece of audio given to Whisper at once (its spectrogram is held whole in memory).
CHUNK_SECONDS = 600.0
# Punctuation that closes what came before it.
_CLOSING = ".,;:!?…)»"


@dataclass(frozen=True)
class SpeechTranscript:
    words: tuple[TimedWord, ...]
    speech: tuple[tuple[float, float], ...]  # where the voice detector hears speech
    dropped: tuple[tuple[float, float, str], ...]  # text the guards threw away
    model: str
    unsure_speaker: tuple[float, ...] = ()  # where the voices could not be told apart


def transcribe_speech(
    audio: Path,
    language: str,
    *,
    model: str = "auto",
    beam_size: int = 5,
    whisper: Any = None,
    speech: Sequence[tuple[float, float]] | None = None,
    chunk_seconds: float = CHUNK_SECONDS,
) -> SpeechTranscript:
    """Words with times and confidence; `speech` regions are detected unless given.

    faster-whisper works out the spectrogram of all the audio it is given at once: for an hour,
    gigabytes. The audio goes to it in pieces of at most `chunk_seconds`, cut in silences."""
    samples = load_mono16k(audio)
    regions = tuple(speech) if speech is not None else speech_regions(samples)
    name = model if model != "auto" else DEFAULT_SPEECH_MODEL.get(language, "large-v3-turbo")
    transcriber = WhisperTranscriber(model=name, whisper=whisper)
    whisper_model = transcriber.whisper_for_language(language)
    words: list[TimedWord] = []
    dropped: list[tuple[float, float, str]] = []
    kept_texts: list[str] = []
    for first, last in pieces(regions, len(samples) / SAMPLE_RATE, chunk_seconds):
        found, _ = whisper_model.transcribe(
            samples[round(first * SAMPLE_RATE) : round(last * SAMPLE_RATE)],
            language=language,
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
        )
        _keep(found, first, regions, words, dropped, kept_texts)
    transcriber.unload()
    return SpeechTranscript(
        tuple(words), regions, tuple(dropped), transcriber.model_for_language(language)
    )


def pieces(
    regions: Sequence[tuple[float, float]], total: float, limit: float
) -> list[tuple[float, float]]:
    """Stretches of at most `limit` seconds (unless one region is longer), cut halfway through
    the silences between speech regions."""
    out: list[tuple[float, float]] = []
    start = 0.0
    for (_, end), following in itertools.pairwise(regions):
        if following[1] - start > limit:
            cut = (end + following[0]) / 2
            out.append((start, cut))
            start = cut
    out.append((start, total))
    return out


def _keep(
    found: Any,
    offset: float,
    regions: Sequence[tuple[float, float]],
    words: list[TimedWord],
    dropped: list[tuple[float, float, str]],
    kept_texts: list[str],
) -> None:
    """Adds a piece's segments, moved to the whole audio's time, minus what is made up."""
    for segment in found:
        text = " ".join(segment.text.split())
        if not text:
            continue
        start, end = segment.start + offset, segment.end + offset
        repeated = len(kept_texts) >= _MAX_SAME_IN_A_ROW and all(
            t.lower() == text.lower() for t in kept_texts[-_MAX_SAME_IN_A_ROW:]
        )
        made_up = (
            _share(regions, start, end) < MIN_VOICE_SHARE
            or any(p.search(text) for p in HALLUCINATIONS)
            or is_loop(text)
            or repeated
        )
        if made_up:
            dropped.append((round(start, 3), round(end, 3), text))
            continue
        kept_texts.append(text)
        for w in segment.words or ():
            _add_word(words, w.word.strip(), w.start + offset, w.end + offset, w.probability)


def _add_word(
    words: list[TimedWord], text: str, start: float, end: float, probability: float
) -> None:
    """Adds a word, giving back to the previous one the punctuation Whisper glued to its front
    (".E" after "está" is "está." and "E") or a word that is only punctuation ("...")."""
    lead = len(text) - len(text.lstrip(_CLOSING))
    if lead and words:
        last = words[-1]
        words[-1] = TimedWord(last.text + text[:lead], last.start, last.end, last.confidence)
        text = text[lead:]
    if text:
        words.append(TimedWord(text, round(start, 3), round(end, 3), round(probability, 3)))


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
