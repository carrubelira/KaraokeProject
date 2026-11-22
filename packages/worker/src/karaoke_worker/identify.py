"""Which song is this? The `analyze` task, before anything heavy runs (plan v4 §7).

The operator only pastes a link (or drops a file). This works out what it is, step by step, and
offers it for review:

1. **The page or the file**: YouTube Music names the track, the artist and the album; any other
   video only has a title such as «Artist - Title (Official Video)», which is cleaned; a file has
   its tags.
2. **The sound**: a Chromaprint fingerprint of the first two minutes (ffmpeg's `chromaprint`
   muxer, or `fpcalc`), looked up in AcoustID, which answers with MusicBrainz recordings.
3. **MusicBrainz**: the recording's title, artists, first release, year and the language its
   lyrics are written in; the cover comes from the Cover Art Archive.
4. **The lyrics**: LRCLIB, searched with the best name found, closest in duration first.

AcoustID needs an application key (free): `karaoke-worker acoustid-key KEY` keeps it in the
worker's settings, and `KARAOKE_ACOUSTID_KEY` in its environment wins over it. Without it the
sound is not looked up and the analysis says so. Network failures never fail the task: the
operator reviews whatever was found.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

import httpx

from karaoke_worker.titles import clean_artist, clean_title, split_artist

logger = logging.getLogger(__name__)

ACOUSTID_URL = "https://api.acoustid.org/v2/lookup"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2"
COVER_URL = "https://coverartarchive.org/release/{id}/front-250"
FINGERPRINT_SECONDS = 120
MUSICBRAINZ_ATTEMPTS = 4
# AcoustID scores below this are someone else's song more often than not.
MIN_SCORE = 0.5
# ISO 639-3 (MusicBrainz) to the codes the engine uses.
LANGUAGES = {"glg": "gl", "spa": "es", "por": "pt", "eng": "en", "cat": "ca", "eus": "eu",
             "fra": "fr", "ita": "it", "deu": "de", "ast": "ast"}  # fmt: skip
# A few words only one of these languages uses often, to guess the lyrics' language.
_STOPWORDS = {
    "gl": "que non unha do da dos das no na nos nas co coa mais ti eu vou xa moito ou cando",
    "es": "que no una del los las el en con pero yo tú muy cuando porque ya está estoy",
    "pt": "que não uma do da dos das no na com mas eu você muito quando porque já está",
    "en": "the and you that it is in my me your of to on for with this be love",
    "ca": "que no una del dels les els amb però jo tu molt quan perquè ja està",
    "fr": "que ne une des les le la et je tu pas mais avec pour dans est moi",
    "it": "che non una del della gli le il la e io tu ma con per sono questo",
    "de": "und die der das ich du nicht ein eine mit ist mich dich auf wie",
}

Note = Callable[[str, str], None]  # step, line for the operator


@dataclass
class Guess:
    """One idea of what the song is, and how sure its source is (0 to 1)."""

    source: str  # "youtube", "title", "tags", "acoustid"
    title: str
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    language: str | None = None
    confidence: float = 0.0
    cover: str | None = None
    recording: str | None = None


@dataclass
class Analysis:
    guesses: list[Guess] = field(default_factory=list)
    lyrics: list[dict[str, Any]] = field(default_factory=list)
    duration: float | None = None
    fingerprint: str = "skipped"  # "ok", "no_match", "no_key", "failed", "skipped"
    notes: list[str] = field(default_factory=list)

    def result(self) -> dict[str, Any]:
        ranked = sorted(self.guesses, key=lambda g: g.confidence, reverse=True)
        best = asdict(ranked[0]) if ranked else None
        if best is not None and not best.get("language"):
            best["language"] = next((g.language for g in ranked if g.language), None)
            if best["language"] is None and self.lyrics:
                best["language"] = guess_language(self.lyrics[0]["text"])
        return {
            "best": best,
            "candidates": [asdict(g) for g in ranked],
            "lyrics": self.lyrics,
            "duration": self.duration,
            "fingerprint": self.fingerprint,
            "notes": self.notes,
        }


def user_agent() -> str:
    version = metadata.version("karaoke-worker")
    return f"KaraokeProject/{version} ( https://github.com/gaelfernandez1/KaraokeProject )"


def from_page(info: dict[str, Any]) -> list[Guess]:
    """What the video page says, cleaned. A track and artist from YouTube Music are sure; a
    title split as «Artist - Title» less so."""
    guesses = []
    title = str(info.get("title") or "").strip()
    track, artist = info.get("track"), clean_artist(info.get("artist"))
    if track and artist:
        guesses.append(
            Guess(
                "youtube",
                clean_title(str(track)),
                artist,
                info.get("album"),
                info.get("year"),
                confidence=0.8,
                cover=info.get("thumbnail"),
            )
        )
    if title:
        named_artist, name = split_artist(clean_title(title))
        uploader = clean_artist(info.get("uploader"))
        guesses.append(
            Guess(
                "title",
                name,
                named_artist or artist or uploader,
                confidence=0.55 if named_artist else 0.35,
                cover=info.get("thumbnail"),
            )
        )
    return guesses


def from_tags(tags: dict[str, str], filename: str) -> list[Guess]:
    """What an uploaded file's own tags (or its name) say."""
    lowered = {k.lower(): v for k, v in tags.items()}
    if lowered.get("title"):
        year = re.match(r"\d{4}", lowered.get("date", ""))
        return [Guess("tags", lowered["title"], lowered.get("artist"), lowered.get("album"),
                      int(year.group()) if year else None, confidence=0.7)]  # fmt: skip
    artist, name = split_artist(clean_title(Path(filename).stem))
    return [Guess("title", name, artist, confidence=0.4 if artist else 0.25)]


def probe_file(path: Path) -> tuple[float | None, dict[str, str]]:
    """The file's duration and tags, with ffprobe."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, timeout=60, check=True,
        ).stdout  # fmt: skip
        found = json.loads(out).get("format", {})
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, {}
    duration = found.get("duration")
    return (float(duration) if duration else None), dict(found.get("tags") or {})


def fingerprint(path: Path) -> str | None:
    """Chromaprint's compressed fingerprint (base64) of the first two minutes."""
    if shutil.which("fpcalc"):
        try:
            out = subprocess.run(
                ["fpcalc", "-json", "-length", str(FINGERPRINT_SECONDS), str(path)],
                capture_output=True, timeout=120, check=True,
            ).stdout  # fmt: skip
            return str(json.loads(out)["fingerprint"])
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            logger.info("fpcalc could not read the song; trying ffmpeg")
    try:
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-t", str(FINGERPRINT_SECONDS), "-i", str(path), "-ac",
             "2", "-f", "chromaprint", "-fp_format", "base64", "-"],
            capture_output=True, timeout=180, check=True,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return None
    text = out.decode("ascii", "replace").strip()
    return text or None


def acoustid(client: httpx.Client, key: str, print_: str, duration: float) -> list[Guess]:
    answer = client.post(
        ACOUSTID_URL,
        data={"client": key, "duration": int(duration), "fingerprint": print_,
              "meta": "recordings releases releasegroups compress", "format": "json"},
    )  # fmt: skip
    answer.raise_for_status()
    data = answer.json()
    if data.get("status") != "ok":
        raise RuntimeError(str(data.get("error", {}).get("message") or "AcoustID refused"))
    guesses = []
    for result in data.get("results", []):
        score = float(result.get("score") or 0)
        if score < MIN_SCORE:
            continue
        for recording in result.get("recordings", [])[:3]:
            if not recording.get("title"):
                continue
            artists = ", ".join(a["name"] for a in recording.get("artists", []) if a.get("name"))
            releases = recording.get("releases") or []
            first = min(
                releases, key=lambda r: (r.get("date") or {}).get("year") or 9999, default=None
            )
            guesses.append(
                Guess(
                    "acoustid",
                    str(recording["title"]),
                    artists or None,
                    first.get("title") if first else None,
                    (first.get("date") or {}).get("year") if first else None,
                    confidence=round(min(0.98, score), 2),
                    cover=COVER_URL.format(id=first["id"]) if first and first.get("id") else None,
                    recording=recording.get("id"),
                )
            )
    return guesses


def musicbrainz(client: httpx.Client, guess: Guess) -> None:
    """Fills in the language of the lyrics (and the first release) from MusicBrainz."""
    if guess.recording is None:
        return
    # MusicBrainz answers 503 to anyone over one request a second: wait and ask again.
    # `inc` takes its `+` as is (encoded, it is not the list separator).
    url = f"{MUSICBRAINZ_URL}/recording/{guess.recording}?inc=releases+artist-credits&fmt=json"
    for attempt in range(MUSICBRAINZ_ATTEMPTS):
        answer = client.get(url)
        if answer.status_code != 503 or attempt == MUSICBRAINZ_ATTEMPTS - 1:
            break
        time.sleep(1.5 * (attempt + 1))
    answer.raise_for_status()
    data = answer.json()
    releases = sorted(data.get("releases") or [], key=lambda r: r.get("date") or "9999")
    for release in releases:
        code = (release.get("text-representation") or {}).get("language")
        if code in LANGUAGES:
            guess.language = LANGUAGES[code]
            break
    if releases and guess.album is None:
        guess.album = releases[0].get("title")
        guess.cover = COVER_URL.format(id=releases[0]["id"])
    year = re.match(r"\d{4}", releases[0].get("date") or "") if releases else None
    if year and guess.year is None:
        guess.year = int(year.group())
    credit = data.get("artist-credit") or []
    if credit:
        guess.artist = "".join(c.get("name", "") + c.get("joinphrase", "") for c in credit)


def guess_language(text: str) -> str | None:
    words = re.findall(r"[^\W\d_]+", text.lower())
    if len(words) < 20:
        return None
    counts = {lang: sum(1 for w in words if w in set(stop.split())) for lang, stop in
              _STOPWORDS.items()}  # fmt: skip
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] >= 5 else None


def find_lyrics(guess: Guess, duration: float | None) -> list[dict[str, Any]]:
    from karaoke_engine.lyrics_lookup import search_lyrics

    query = f"{guess.artist or ''} {guess.title}".strip()
    return [asdict(c) | {"source": "lrclib"} for c in search_lyrics(query, duration, limit=6)]


async def analyse(
    source: Path,
    page: dict[str, Any] | None,
    given: dict[str, Any],
    note: Note,
    acoustid_key: str | None = None,
) -> dict[str, Any]:
    """Everything above, in order; `note(step, line)` tells the operator what it is doing."""
    found = Analysis()
    key = acoustid_key if acoustid_key is not None else os.environ.get("KARAOKE_ACOUSTID_KEY")
    note("metadata", "Reading what the page and the file say")
    found.duration, tags = await asyncio.to_thread(probe_file, source)
    if page:
        found.duration = found.duration or page.get("duration")
        found.guesses += from_page(page)
    else:
        found.guesses += from_tags(tags, str(given.get("filename") or source.name))
    if given.get("title"):
        found.guesses.append(Guess("operator", given["title"], given.get("artist"),
                                   language=given.get("language"), confidence=1.0))  # fmt: skip
    headers = {"User-Agent": user_agent()}
    with httpx.Client(headers=headers, timeout=20, follow_redirects=True) as client:
        if not key:
            found.fingerprint = "no_key"
            found.notes.append("no_acoustid_key")
            note("fingerprint", "No AcoustID key: the sound is not looked up")
        elif found.duration:
            note("fingerprint", "Listening to the first two minutes (Chromaprint)")
            print_ = await asyncio.to_thread(fingerprint, source)
            if print_ is None:
                found.fingerprint = "failed"
                note("fingerprint", "Could not take the song's fingerprint")
            else:
                note("acoustid", "Looking the fingerprint up in AcoustID")
                try:
                    heard = await asyncio.to_thread(acoustid, client, key, print_, found.duration)
                except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                    found.fingerprint = "failed"
                    note("acoustid", f"AcoustID did not answer: {exc}")
                    heard = []
                else:
                    found.fingerprint = "ok" if heard else "no_match"
                    note("acoustid", f"AcoustID knows {len(heard)} recording(s)")
                if heard:
                    note("musicbrainz", f"MusicBrainz: «{heard[0].title}»")
                    try:
                        await asyncio.to_thread(musicbrainz, client, heard[0])
                    except (httpx.HTTPError, ValueError) as exc:
                        note("musicbrainz", f"MusicBrainz did not answer: {exc}")
                found.guesses += heard
    best = max(found.guesses, key=lambda g: g.confidence, default=None)
    if best is not None:
        note("lyrics", f"Searching LRCLIB for «{best.artist or '?'} - {best.title}»")
        try:
            found.lyrics = await asyncio.to_thread(find_lyrics, best, found.duration)
        except Exception as exc:  # noqa: BLE001 - LRCLIB being down is not the song's fault
            note("lyrics", f"LRCLIB did not answer: {exc}")
        note("lyrics", f"{len(found.lyrics)} lyrics found")
    return found.result()
