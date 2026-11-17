"""Word times from the Galician CTC aligner instead of Whisper's.

Whisper's word times run early: on the bench dialogues a caption came in 0.38 s before the voice
(median), from 0.76 to 0.07 s. The aligner the karaoke uses for lyrics (wav2vec2, Galician model
for Galician) places letters on the audio to a few hundredths of a second. Here it places the
words Whisper heard: the emissions of the whole recording are worked out once (only the letters
the words use), and each stretch of words between pauses is aligned on its own slice with some
margin around it, so an hour costs no more memory than a minute. A word whose letters the model
does not see (its alignment is too unlikely) or that would move far keeps Whisper's time.
"""

import math
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from karaoke_engine.align.audio import load_mono16k
from karaoke_engine.align.ctc import Segment, align_segments
from karaoke_engine.align.emissions import EmissionModel, Vocab
from karaoke_engine.align.models import DEFAULT_BY_LANGUAGE, FALLBACK_MODEL, MODELS
from karaoke_engine.align.spoken import spoken
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import SpeechTranscript

_PAD = 0.8  # seconds of audio on each side of a stretch: Whisper is up to this far off
_PAUSE = 0.3  # stretches are split at pauses this long
_LONGEST = 30.0  # and are at most this long
_FILLER = 3.0  # cost per frame of sound outside the words (the lyrics aligner's)
_MIN_CONFIDENCE = 0.05  # mean letter probability under which a word keeps Whisper's time
_MAX_SHIFT = 1.0


def refine_words(
    audio: Path, transcript: SpeechTranscript, *, language: str = "gl", model: Any = None
) -> SpeechTranscript:
    """The transcript with each word's start and end from the CTC aligner, where it is sure."""
    words = list(transcript.words)
    if not words:
        return transcript
    net = model or EmissionModel(MODELS[DEFAULT_BY_LANGUAGE.get(language, FALLBACK_MODEL)])
    net.load()
    try:
        vocab: Vocab = net.vocab
        letters = [_letters(w.text, vocab, language) for w in words]
        used = sorted({t for ids in letters for t in ids} | _delimiter(vocab))
        if not any(letters):
            return transcript
        column = {t: i + 2 for i, t in enumerate(used)}
        emissions = net.emissions(load_mono16k(audio), used)
    finally:
        net.unload()
    seconds = emissions.frame_seconds
    frames = len(emissions.log_probs)
    for stretch in _stretches(words):
        ids: list[int] = []
        owner: list[int] = []
        for k in stretch:
            if not letters[k]:
                continue
            if ids and vocab.delimiter is not None:
                ids.append(column[vocab.delimiter])
                owner.append(-1)
            ids += [column[t] for t in letters[k]]
            owner += [k] * len(letters[k])
        if not ids:
            continue
        first = max(0, math.floor((words[stretch[0]].start - _PAD) / seconds))
        last = min(frames, math.ceil((words[stretch[-1]].end + _PAD) / seconds))
        log_probs = emissions.log_probs[first:last]
        [path] = align_segments(log_probs, [Segment(tuple(ids), tuple(owner), math.inf)], _FILLER)
        if path.spans is None:
            continue
        for k in stretch:
            mine = [i for i, o in enumerate(owner) if o == k]
            if not mine:
                continue
            spans = [path.spans[i] for i in mine]
            total = sum(
                float(log_probs[a : b + 1, ids[i]].sum())
                for i, (a, b) in zip(mine, spans, strict=True)
            )
            count = sum(b - a + 1 for a, b in spans)
            start = (first + spans[0][0]) * seconds
            end = (first + spans[-1][1] + 1) * seconds
            sure = math.exp(total / count) >= _MIN_CONFIDENCE
            if sure and abs(start - words[k].start) <= _MAX_SHIFT:
                words[k] = replace(words[k], start=round(start, 3), end=round(end, 3))
    return replace(transcript, words=tuple(words))


def refine_in_child(audio: Path, transcript: SpeechTranscript) -> SpeechTranscript:
    """refine_words in a fresh process, so the model's memory goes back to the system."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        try:
            return pool.submit(refine_words, audio, transcript).result()
        except BrokenProcessPool as exc:
            raise MemoryError(
                "the aligner process was killed (out of memory?): close other programs"
            ) from exc


def _letters(text: str, vocab: Vocab, language: str) -> tuple[int, ...]:
    ids: list[int] = []
    for piece in spoken(text, language).split():
        ids += vocab.encode(piece)
    return tuple(ids)


def _delimiter(vocab: Vocab) -> set[int]:
    return {vocab.delimiter} if vocab.delimiter is not None else set()


def _stretches(words: Sequence[TimedWord]) -> list[list[int]]:
    """Runs of words with no pause of _PAUSE between them, of at most _LONGEST seconds."""
    runs: list[list[int]] = []
    for k, word in enumerate(words):
        if runs:
            previous = words[runs[-1][-1]]
            joined = word.start - previous.end < _PAUSE
            if joined and word.end - words[runs[-1][0]].start <= _LONGEST:
                runs[-1].append(k)
                continue
        runs.append([k])
    return runs
