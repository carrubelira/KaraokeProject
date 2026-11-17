"""SRT and WebVTT, the two files that travel next to the video.

The SRT is for editors and players (DaVinci Resolve, Premiere, VLC): UTF-8 with a byte order mark
and CRLF line ends, which Windows tools read without mangling accents. The WebVTT is for the web
and for the archive: a NOTE says how it was made, and a voice tag says who speaks.
"""

import re
from collections.abc import Mapping, Sequence

from karaoke_engine.captions.rules import Caption

SRT_ENCODING = "utf-8-sig"
_CUE_TIME = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})"
)
_TAG = re.compile(r"<[^>]*>|\{\\[^}]*\}")


def to_srt(captions: Sequence[Caption]) -> str:
    blocks = [
        f"{i}\r\n{_stamp(c.start, ',')} --> {_stamp(c.end, ',')}\r\n" + "\r\n".join(c.lines)
        for i, c in enumerate(captions, 1)
    ]
    return "".join(block + "\r\n\r\n" for block in blocks)


def to_vtt(captions: Sequence[Caption], note: str, labels: Mapping[str, str]) -> str:
    out = ["WEBVTT\n"]
    if note:
        out.append("NOTE\n" + note.replace("-->", "->") + "\n")
    for c in captions:
        out.append(
            f"{_stamp(c.start, '.')} --> {_stamp(c.end, '.')}\n" + _vtt_text(c, labels) + "\n"
        )
    return "\n".join(out)


def read_srt(text: str) -> list[Caption]:
    """Captions from an SRT as editors export it: any numbering, BOM, CRLF, `.` or `,`."""
    captions: list[Caption] = []
    lines = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        match = _CUE_TIME.search(lines[i])
        if match is None:
            i += 1
            continue
        start, end = _seconds(match.groups()[:4]), _seconds(match.groups()[4:])
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip():
            body.append(_TAG.sub("", lines[i]).strip())
            i += 1
        body = [line for line in body if line]
        if body:
            captions.append(Caption(start, end, tuple(body), (None,) * len(body)))
    if not captions:
        raise ValueError("no subtitles found in this SRT")
    return captions


def _vtt_text(caption: Caption, labels: Mapping[str, str]) -> str:
    lines = [_escape(line) for line in caption.lines]
    names = [labels.get(s) if s is not None else None for s in caption.speakers]
    if len(set(names)) > 1:
        return "\n".join(
            f"<v {name}>{line}</v>" if name else line
            for name, line in zip(names, lines, strict=True)
        )
    if names and names[0]:
        lines[0] = f"<v {names[0]}>{lines[0]}"
    return "\n".join(lines)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _stamp(seconds: float, mark: str) -> str:
    total = round(seconds * 1000)
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{mark}{millis:03d}"


def _seconds(parts: Sequence[str]) -> float:
    hours, minutes, secs, fraction = parts
    millis = int(fraction.ljust(3, "0"))
    return round(int(hours) * 3600 + int(minutes) * 60 + int(secs) + millis / 1000, 3)
