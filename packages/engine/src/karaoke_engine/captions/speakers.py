"""Who speaks: the interviewee (A) and the interviewer (B), told apart by their voices.

Each stretch of speech is cut into windows of 1.5 s every 0.75 s, each window gets a voice print
(an x-vector from a speaker verification model), and the prints are split into two groups by
direction (k-means on the cosine, several starts, fixed seed). The group that talks more is the
interviewee. Two groups whose centres point the same way are one voice: a monologue. Each word
takes the group of the window nearest its middle, and a "turn" of less than a second between
two stretches of the same voice is taken as a mistake and joins them. Where a window sits nearly
halfway between the two voices, the review list asks who is speaking.

The voice print model is `anton-l/wav2vec2-base-superb-sv` (Apache-2.0): WavLM's speaker model
would tell voices apart better, but its weights are CC BY-SA, which this project does not take.
"""

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import SpeechTranscript

MODEL = ("anton-l/wav2vec2-base-superb-sv", "eb0be47779dda10620d068ab579fca970ee7e417")
_WINDOW = 1.5
_HOP = 0.75
_SHORTEST = 0.4  # a stretch of speech shorter than this gets no voice print
_SAME_VOICE = 0.9  # cosine between the two centres above which they are one voice
_SHORTEST_TURN = 1.0
# Cosine difference between the two voices under which it is unsure (not tuned: the bench has
# no overlapping speech; checked on the real interviews).
_UNSURE_MARGIN = 0.1
_STARTS = 10
_ROUNDS = 30

Embed = Callable[[Sequence[npt.NDArray[np.float32]]], npt.NDArray[np.float32]]


def assign_speakers(
    audio: Path, transcript: SpeechTranscript, *, embed: Embed | None = None
) -> SpeechTranscript:
    """The transcript with each word's speaker ("A" talks more, "B" asks)."""
    windows = _windows(transcript.speech)
    if not windows or not transcript.words:
        return transcript
    samples = load_mono16k(audio)
    pieces = [samples[round(a * SAMPLE_RATE) : round(b * SAMPLE_RATE)] for a, b in windows]
    prints = (embed or _XVector())(pieces)
    prints = prints / (np.linalg.norm(prints, axis=1, keepdims=True) + 1e-9)
    groups, centres = _two_groups(prints)
    if float(centres[0] @ centres[1]) > _SAME_VOICE:
        return replace(transcript, words=tuple(replace(w, speaker="A") for w in transcript.words))
    seconds = [
        sum(b - a for (a, b), g in zip(windows, groups, strict=True) if g == k) for k in (0, 1)
    ]
    talker = 0 if seconds[0] >= seconds[1] else 1
    scores = prints @ centres.T  # cosine to each centre, per window
    middles = np.array([(a + b) / 2 for a, b in windows])
    labels: list[str] = []
    margins: list[float] = []
    for word in transcript.words:
        k = int(np.argmin(np.abs(middles - (word.start + word.end) / 2)))
        labels.append("A" if groups[k] == talker else "B")
        margins.append(float(abs(scores[k, 0] - scores[k, 1])))
    labels = _smooth(transcript.words, labels)
    words = tuple(replace(w, speaker=s) for w, s in zip(transcript.words, labels, strict=True))
    return _with_unsure(transcript, words, margins)


def _with_unsure(
    transcript: SpeechTranscript, words: tuple[TimedWord, ...], margins: Sequence[float]
) -> SpeechTranscript:
    """The transcript with these words, and the start of each run of words the voices blur."""
    unsure: list[float] = []
    previous = False
    for word, margin in zip(words, margins, strict=True):
        blurred = margin < _UNSURE_MARGIN
        if blurred and not previous:
            unsure.append(word.start)
        previous = blurred
    return replace(transcript, words=words, unsure_speaker=tuple(unsure))


def speakers_in_child(audio: Path, transcript: SpeechTranscript) -> SpeechTranscript:
    """assign_speakers in a fresh process, so the model's memory goes back to the system."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        try:
            return pool.submit(assign_speakers, audio, transcript).result()
        except BrokenProcessPool as exc:
            raise MemoryError(
                "the speaker process was killed (out of memory?): close other programs"
            ) from exc


def _windows(speech: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for start, end in speech:
        if end - start < _SHORTEST:
            continue
        if end - start <= _WINDOW:
            out.append((start, end))
            continue
        t = start
        while t + _WINDOW <= end:
            out.append((t, t + _WINDOW))
            t += _HOP
        if out[-1][1] < end:
            out.append((end - _WINDOW, end))
    return out


def _two_groups(
    prints: npt.NDArray[np.float32],
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float32]]:
    """Two groups of unit vectors by direction: the best of several k-means runs."""
    rng = np.random.default_rng(0)
    best: tuple[float, npt.NDArray[np.int64], npt.NDArray[np.float32]] | None = None
    if len(prints) == 1:
        return np.zeros(1, dtype=np.int64), np.stack([prints[0], prints[0]])
    for _ in range(_STARTS):
        centres = prints[rng.choice(len(prints), size=2, replace=False)].copy()
        for _ in range(_ROUNDS):
            groups = np.argmax(prints @ centres.T, axis=1)
            moved = np.stack(
                [
                    prints[groups == k].mean(axis=0) if np.any(groups == k) else centres[k]
                    for k in (0, 1)
                ]
            )
            moved /= np.linalg.norm(moved, axis=1, keepdims=True) + 1e-9
            if np.allclose(moved, centres):
                break
            centres = moved
        spread = float((1 - (prints @ centres.T).max(axis=1)).sum())
        if best is None or spread < best[0]:
            best = (spread, groups, centres)
    assert best is not None
    return best[1], best[2]


def _smooth(words: Sequence[TimedWord], labels: list[str]) -> list[str]:
    """A run of words shorter than a second between two runs of the other voice joins them."""
    runs: list[list[int]] = []
    for i, label in enumerate(labels):
        if runs and labels[runs[-1][0]] == label:
            runs[-1].append(i)
        else:
            runs.append([i])
    out = list(labels)
    for r in range(1, len(runs) - 1):
        run = runs[r]
        before, after = labels[runs[r - 1][0]], labels[runs[r + 1][0]]
        if before == after and words[run[-1]].end - words[run[0]].start < _SHORTEST_TURN:
            for i in run:
                out[i] = before
    return out


class _XVector:
    """Voice prints from a speaker verification model, on the graphics card if there is one."""

    def __init__(self) -> None:
        import torch
        from transformers import AutoFeatureExtractor, Wav2Vec2ForXVector

        repo, revision = MODEL
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        # Untyped in transformers, missing without the ml extra: Any either way.
        extractor: Any = AutoFeatureExtractor
        model: Any = Wav2Vec2ForXVector
        self._features = extractor.from_pretrained(repo, revision=revision)
        self._net = model.from_pretrained(repo, revision=revision).to(self._device).eval()

    def __call__(self, windows: Sequence[npt.NDArray[np.float32]]) -> npt.NDArray[np.float32]:
        import torch

        out = []
        for i in range(0, len(windows), 32):
            batch = [np.asarray(w, dtype=np.float32) for w in windows[i : i + 32]]
            inputs = self._features(
                batch, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True
            )
            with torch.inference_mode():
                found = self._net(**{k: v.to(self._device) for k, v in inputs.items()})
            out.append(found.embeddings.float().cpu().numpy())
        return np.concatenate(out).astype(np.float32)
