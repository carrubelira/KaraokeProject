"""Where the separated vocals actually sound, from their loudness alone.

The separator leaves a little of the band in the vocals, so "voice" means loud compared with the
song's own singing, not merely not silent. Short dips inside a phrase (a stop consonant, a
breath) stay voice; short blips in a break are dropped.
"""

import itertools
import math

import numpy as np
import numpy.typing as npt

# Below this the vocals are silent whatever the song's level (dBFS).
_FLOOR_DB = -60.0
_FILL_GAPS = 0.15
_MIN_BURST = 0.1


def vocal_activity(
    samples: npt.NDArray[np.float32],
    rate: int = 16000,
    hop: float = 0.02,
    threshold_db: float = -35.0,
) -> npt.NDArray[np.bool_]:
    """One flag per `hop` seconds: True where the voice is within `threshold_db` of its peak."""
    size = round(hop * rate)
    count = -(-len(samples) // size)
    padded = np.zeros(count * size, dtype=np.float32)
    padded[: len(samples)] = samples
    rms = np.sqrt(np.mean(padded.reshape(count, size).astype(np.float64) ** 2, axis=1))
    level = 20 * np.log10(rms + 1e-10)
    peak = float(np.percentile(level, 95)) if count else _FLOOR_DB
    active = (level > max(peak + threshold_db, _FLOOR_DB)) & (peak > _FLOOR_DB)
    active = _fill_runs(active, value=False, shorter_than=round(_FILL_GAPS / hop), inner_only=True)
    return _fill_runs(active, value=True, shorter_than=round(_MIN_BURST / hop), inner_only=False)


def voiced_stretches(
    active: npt.NDArray[np.bool_],
    hop: float = 0.02,
    limit: float = 30.0,
    min_gap: float = 0.5,
    max_gap: float = 7.0,
    pad: float = 0.25,
) -> list[tuple[float, float]]:
    """Stretches of singing of at most `limit` seconds, in seconds, cut where the voice rests.

    A transcriber reads half a minute at a time. Fed a whole song, it cuts its windows wherever
    they fall, through a sung phrase too, and that is where it drops lines or makes them up.
    Here phrases less than `min_gap` apart stay together, neighbours join while the stretch fits
    in `limit` and no silence inside is longer than `max_gap`, and a phrase that is too long by
    itself is cut at its longest pause (evenly, if it has none). Each stretch gets up to `pad`
    seconds of margin, never past half the silence next to it.
    """
    runs = _true_runs(active)
    if not runs:
        return []
    phrases = [runs[0]]
    for start, end in runs[1:]:
        if (start - phrases[-1][1]) * hop < min_gap:
            phrases[-1] = (phrases[-1][0], end)
        else:
            phrases.append((start, end))
    most = max(round(limit / hop), 1)
    pieces = [piece for phrase in phrases for piece in _fit(phrase, active, most)]
    stretches = [pieces[0]]
    for start, end in pieces[1:]:
        first, last = stretches[-1]
        if end - first <= most and 0 < (start - last) * hop <= max_gap:
            stretches[-1] = (first, end)
        else:
            stretches.append((start, end))
    out = []
    for index, (start, end) in enumerate(stretches):
        before = (start - stretches[index - 1][1]) / 2 if index else start
        after = (stretches[index + 1][0] - end) / 2 if index + 1 < len(stretches) else math.inf
        left = max(start * hop - min(pad, before * hop), 0.0)
        right = min(end * hop + min(pad, after * hop), len(active) * hop)
        out.append((round(left, 3), round(right, 3)))
    return out


def _fit(
    phrase: tuple[int, int], active: npt.NDArray[np.bool_], most: int
) -> list[tuple[int, int]]:
    """A phrase in pieces of at most `most` frames: cut at its longest pause, or evenly."""
    start, end = phrase
    if end - start <= most:
        return [phrase]
    pauses = [(a + start, b + start) for a, b in _true_runs(~active[start:end])]
    if pauses:
        first, last = max(pauses, key=lambda pause: pause[1] - pause[0])
        return _fit((start, first), active, most) + _fit((last, end), active, most)
    count = math.ceil((end - start) / most)
    edges = [start + round(k * (end - start) / count) for k in range(count + 1)]
    return list(itertools.pairwise(edges))


def _true_runs(flags: npt.NDArray[np.bool_]) -> list[tuple[int, int]]:
    """First frame and the frame after the last one of each run of True."""
    edges = np.diff(np.concatenate([[0], flags.astype(np.int8), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), ends.tolist(), strict=True))


def _fill_runs(
    flags: npt.NDArray[np.bool_], value: bool, shorter_than: int, inner_only: bool
) -> npt.NDArray[np.bool_]:
    """Flips runs of `value` shorter than `shorter_than` frames (only between others if inner)."""
    out = flags.copy()
    n = len(flags)
    i = 0
    while i < n:
        if flags[i] != value:
            i += 1
            continue
        j = i
        while j < n and flags[j] == value:
            j += 1
        inner = i > 0 and j < n
        if j - i < shorter_than and (inner or not inner_only):
            out[i:j] = not value
        i = j
    return out
