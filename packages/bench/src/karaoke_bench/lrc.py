"""References timed line by line, from synchronised lyrics (LRC).

Open lyrics databases such as LRCLIB hold songs whose lines someone timed while listening: one
time per line, at the moment it starts. That is no word timing, but it is a hand-made check of
where every line begins, for songs nobody will time word by word. Only the first word of each
line is scored, and only its start; like any timing tapped by hand it is good to a few tenths
of a second.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from karaoke_bench.reference import Reference, RefLine, RefWord

# [mm:ss.xx], also [mm:ss] and [mm:ss:xx]; tags such as [ar: Name] have no digits there.
_STAMP = re.compile(r"\[(\d+):(\d+)(?:[.:](\d+))?\]")


@dataclass(frozen=True)
class LrcEntry:
    start: float
    text: str  # empty when the entry only marks where the line before it ends


def parse_lrc(text: str) -> list[LrcEntry]:
    """Timed entries in time order; a line written with several times comes out once for each."""
    entries = []
    for row in text.replace("\r", "").lstrip("﻿").split("\n"):
        rest = row.strip()
        starts = []
        while match := _STAMP.match(rest):
            minutes, seconds, fraction = match.groups()
            starts.append(int(minutes) * 60 + int(seconds) + float(f"0.{fraction or 0}"))
            rest = rest[match.end() :].lstrip()
        entries += [LrcEntry(round(start, 3), rest) for start in starts]
    return sorted(entries, key=lambda entry: entry.start)


def reference_from_lrc(
    entries: Sequence[LrcEntry], song_id: str, language: str, duration: float
) -> Reference:
    """A line per entry with words; each ends where the next entry (with or without text) starts."""
    lines = []
    for index, entry in enumerate(entries):
        words = entry.text.split()
        if not any(ch.isalnum() for ch in entry.text):
            continue
        if entry.start >= duration:
            raise ValueError(
                f"the line at {entry.start:.1f} s starts after the audio ends ({duration:.1f} s): "
                "these lyrics were timed for another recording"
            )
        later = (other.start for other in entries[index + 1 :] if other.start > entry.start)
        end = min(next(later, duration), duration)
        lines.append(
            RefLine(
                text=entry.text,
                start=entry.start,
                end=end,
                # Every word carries the line's span: only the first one's start is scored.
                words=[RefWord(text=word, start=entry.start, end=end) for word in words],
            )
        )
    if not lines:
        raise ValueError("no timed lines: an LRC file has a [mm:ss.xx] time before each line")
    return Reference(
        song_id=song_id,
        language=language,
        duration=duration,
        timing="lines",
        approved=True,
        lines=lines,
    )
