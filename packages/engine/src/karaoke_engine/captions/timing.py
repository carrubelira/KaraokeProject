"""When each caption comes in and goes out, on the video's frames.

The work is done in whole frames, as an editor's timeline does. A caption comes in with its first
word, or on a cut close to it. It stays up to half a second after its last word, closing the gap
to two frames when the next caption is near (chained captions do not flicker), and ending two
frames before a nearby cut, as long as that does not hide words still being said. Short captions
are lengthened to be readable. Captions never overlap or go backwards, even when two people
talk at once.
"""

import math
from collections.abc import Sequence
from dataclasses import replace

from karaoke_engine.captions.rules import Caption, Rules


def time_captions(
    captions: Sequence[Caption],
    rules: Rules,
    fps: float,
    shots: Sequence[float] = (),
    duration: float | None = None,
) -> list[Caption]:
    """The captions with their final in and out times, each on a frame boundary."""
    if not captions:
        return []
    gap = rules.min_gap_frames
    linger = math.floor(rules.linger * fps + 1e-9)
    min_len = math.ceil(rules.min_duration * fps - 1e-9)
    max_len = math.floor(rules.max_duration * fps + 1e-9)
    cuts = sorted(round(t * fps) for t in shots)
    last = math.floor(duration * fps + 1e-9) if duration is not None else None

    starts: list[int] = []
    for caption in captions:
        start = round(caption.start * fps)
        cut = _nearest(cuts, start, rules.shot_snap_frames)
        if cut is not None:
            start = cut
        if starts:
            start = max(start, starts[-1] + gap + 1)
        starts.append(start)

    out: list[Caption] = []
    previous_end: int | None = None
    for i, caption in enumerate(captions):
        start = starts[i]
        following = starts[i + 1] if i + 1 < len(starts) else None
        limit = following - gap if following is not None else last
        spoken = round(caption.end * fps)
        end = spoken + linger
        cut = _nearest(cuts, end, rules.shot_snap_frames)
        if cut is not None and cut - gap >= spoken:
            end = cut - gap
        end = max(end, start + min_len)
        # Chained after lengthening too: a short caption made readable must not leave a flicker.
        if following is not None and following - end < rules.chain_gap * fps:
            end = following - gap
        end = min(end, start + max_len)
        if limit is not None:
            end = min(end, limit)
        if end - start < min_len:
            floor = previous_end + gap if previous_end is not None else 0
            start = max(min(start, end - min_len), floor)
        end = max(end, start + 1)
        out.append(replace(caption, start=round(start / fps, 3), end=round(end / fps, 3)))
        previous_end = end
    return out


def cps(caption: Caption) -> float:
    """Reading speed: characters on screen (line breaks aside) per second."""
    seconds = caption.end - caption.start
    characters = sum(len(line) for line in caption.lines)
    return characters / seconds if seconds > 0 else math.inf


def _nearest(cuts: Sequence[int], frame: int, reach: int) -> int | None:
    near = [cut for cut in cuts if abs(cut - frame) <= reach]
    return min(near, key=lambda cut: abs(cut - frame)) if near else None
