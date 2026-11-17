"""Lyrics from LRCLIB (lrclib.net), an open and free lyrics database, only when asked for.

It sends the title and the artist to that service, never the audio. A song that comes from a
video is named the way video pages name it («Artist - Title (Official Video)»), which the
database does not know: the name is asked as it came, then as the song is probably called, and
last as a free search. Among the entries, the one whose duration is closest to the song's is
taken, because the same song often appears in several edits. The service is sometimes busy: it
is asked again a couple of times.
"""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

URL = "https://lrclib.net/api/search"
USER_AGENT = "karaoke-engine (local karaoke generator)"
# Entries whose duration differs more than this are another edit of the song...
MAX_DURATION_GAP = 5.0
# ...unless it is the audio given that is longer, by no more than this: the video of a song
# often opens with a spoken scene or closes with credits, and its lyrics are the same.
MAX_LONGER_VIDEO = 60.0
_ATTEMPTS = 3
# What separates the parts of a video title, always between spaces («Sen-ti-do» is one word).
_SEPARATORS = re.compile(r"\s+(?:-|\u2013|\u2014|//|\|)\s+")
_BRACKETS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
_VIDEO_WORDS = re.compile(
    r"\b(official|oficial|music|video|vídeo|videoclip|clip|lyrics?|letra|audio|visuali[sz]er|"
    r"hd|4k|mv|remaster(?:ed|izado)?)\b",
    re.IGNORECASE,
)
_FEATURING = re.compile(r"\s+[\(\[]?(?:ft\.?|feat\.?|featuring)\s.*$", re.IGNORECASE)

Fetch = Callable[[str], tuple[int, bytes]]


@dataclass(frozen=True)
class FoundLyrics:
    text: str
    synced: str | None  # LRC with line times, when the entry has them
    source_id: int
    duration: float


def find_lyrics(
    title: str,
    artist: str,
    duration: float,
    fetch: Fetch | None = None,
    wait: Callable[[float], None] = time.sleep,
) -> FoundLyrics | None:
    get = fetch or _http_get
    names = song_names(title, artist)
    questions = [{"track_name": name, "artist_name": artist} for name in [title, *names]]
    asked: list[dict[str, str]] = []
    anything = False
    for question in questions:
        if question in asked:
            continue
        asked.append(question)
        entries = _ask(f"{URL}?{urllib.parse.urlencode(question)}", get, wait)
        anything = anything or bool(entries)
        if (found := _closest(entries, duration)) is not None:
            return found
    if anything or not names:
        return None  # the song is there, in another edit: a free search would find the same
    query = urllib.parse.urlencode({"q": f"{artist} {names[0]}"})
    by_artist = [
        entry
        for entry in _ask(f"{URL}?{query}", get, wait)
        if _within(artist, str(entry.get("artistName") or ""))
    ]
    return _closest(by_artist, duration)


def song_names(title: str, artist: str) -> list[str]:
    """What the song is probably called, from how a video page or a file names it: without the
    artist in front or behind, the kind of video and the guests; then without brackets."""
    parts = []
    for part in _SEPARATORS.split(title):
        plain = _BRACKETS.sub(lambda m: "" if _VIDEO_WORDS.search(m.group()) else m.group(), part)
        plain = _FEATURING.sub("", plain).strip()
        if plain and not _within(artist, plain) and _fold(_VIDEO_WORDS.sub(" ", plain)):
            parts.append(plain)
    name = " - ".join(parts) or title.strip()
    bare = _BRACKETS.sub("", name).strip()
    return [name] if not bare or bare == name else [name, bare]


def _closest(entries: list[dict[str, Any]], duration: float) -> FoundLyrics | None:
    """The entry of the same edit closest in duration; failing that, the longest one the audio
    outlasts by no more than a video's opening and credits."""
    gaps = [
        (duration - float(entry.get("duration") or 0), entry)
        for entry in entries
        if entry.get("plainLyrics")
    ]
    same = [(abs(gap), entry) for gap, entry in gaps if abs(gap) <= MAX_DURATION_GAP]
    longer = [(gap, entry) for gap, entry in gaps if MAX_DURATION_GAP < gap <= MAX_LONGER_VIDEO]
    if not same and not longer:
        return None
    best = min(same or longer, key=lambda item: item[0])[1]
    return FoundLyrics(
        text=str(best["plainLyrics"]),
        synced=best.get("syncedLyrics"),
        source_id=int(best["id"]),
        duration=float(best["duration"]),
    )


def _within(name: str, text: str) -> bool:
    """Whether a name appears in a text as whole words, whatever the case and the accents."""
    words, inside = _fold(name).split(), _fold(text).split()
    return bool(words) and any(
        inside[i : i + len(words)] == words for i in range(len(inside) - len(words) + 1)
    )


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    kept = "".join(ch if ch.isalnum() else " " for ch in plain if not unicodedata.combining(ch))
    return " ".join(kept.split())


def _ask(url: str, fetch: Fetch, wait: Callable[[float], None]) -> list[dict[str, Any]]:
    for attempt in range(_ATTEMPTS):
        status, body = fetch(url)
        if status == 200:
            data = json.loads(body)
            return data if isinstance(data, list) else []
        if status not in (429, 502, 503):
            raise OSError(f"LRCLIB answered {status}")
        if attempt + 1 < _ATTEMPTS:
            wait(2.0 * (attempt + 1))
    raise OSError("LRCLIB is busy; try again later or pass the lyrics with --lyrics")


def _http_get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 - fixed https URL
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed https URL
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()
