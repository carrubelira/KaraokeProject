"""Which song is it: page metadata, file tags, AcoustID answers and the lyrics' language."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from karaoke_worker import identify
from karaoke_worker.identify import Guess, acoustid, from_page, from_tags, guess_language

pytestmark = pytest.mark.anyio


def test_youtube_music_metadata_is_trusted_more_than_a_video_title() -> None:
    page = {"title": "Los Suaves - Pálida Luna (Videoclip Oficial)", "track": "Pálida Luna",
            "artist": "Los Suaves", "album": "Ese Gran Silencio", "uploader": "Los Suaves - Topic",
            "thumbnail": "https://i.ytimg.com/x.jpg"}  # fmt: skip
    music, title = from_page(page)
    assert (music.source, music.title, music.artist, music.album) == (
        "youtube",
        "Pálida Luna",
        "Los Suaves",
        "Ese Gran Silencio",
    )
    assert (title.title, title.artist) == ("Pálida Luna", "Los Suaves")
    assert music.confidence > title.confidence


def test_a_bare_video_title_falls_back_to_the_channel() -> None:
    [guess] = from_page({"title": "Pandeireta (Videoclip Oficial)", "uploader": "Banda - Topic"})
    assert (guess.title, guess.artist) == ("Pandeireta", "Banda")
    assert guess.confidence < 0.5


def test_file_tags_win_over_its_name() -> None:
    [tagged] = from_tags({"TITLE": "Cantiga", "ARTIST": "Banda", "date": "1998-02-01"}, "x.mp3")
    assert (tagged.title, tagged.artist, tagged.year) == ("Cantiga", "Banda", 1998)
    [named] = from_tags({}, "03. Banda - Cantiga.mp3")
    assert (named.title, named.artist) == ("Cantiga", "Banda")


def test_acoustid_answers_become_guesses_with_their_score() -> None:
    answer = {
        "status": "ok",
        "results": [
            {"score": 0.93, "recordings": [{
                "id": "rec-1", "title": "Pálida luna", "artists": [{"name": "Los Suaves"}],
                "releases": [{"id": "rel-2", "title": "Live", "date": {"year": 2001}},
                             {"id": "rel-1", "title": "Ese gran silencio", "date": {"year": 1988}}],
            }]},
            {"score": 0.2, "recordings": [{"id": "rec-x", "title": "Another song"}]},
        ],
    }  # fmt: skip
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(200, json=answer)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        [guess] = acoustid(client, "KEY", "AQAAfingerprint", 245.4)
    assert (seen["client"], seen["duration"], seen["fingerprint"]) == (
        "KEY",
        "245",
        "AQAAfingerprint",
    )
    assert (guess.title, guess.artist, guess.album, guess.year) == (
        "Pálida luna",
        "Los Suaves",
        "Ese gran silencio",
        1988,
    )
    assert guess.confidence == 0.93
    assert guess.cover == identify.COVER_URL.format(id="rel-1")


def test_musicbrainz_gives_the_language_of_the_lyrics() -> None:
    release = {"id": "r", "title": "A", "date": "1990", "text-representation": {"language": "glg"}}
    credit = [{"name": "Uxía", "joinphrase": " & "}, {"name": "Banda"}]
    recording = {"releases": [release], "artist-credit": credit}
    guess = Guess("acoustid", "Cantiga", recording="rec-1")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ws/2/recording/rec-1"
        return httpx.Response(200, json=recording)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        identify.musicbrainz(client, guess)
    assert (guess.language, guess.artist, guess.album) == ("gl", "Uxía & Banda", "A")


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Eu non sei se ti vés cando a lúa sae, pero vou contigo xa " * 3, "gl"),
        ("Yo no sé si tú vienes cuando la luna sale, pero ya estoy aquí " * 3, "es"),
        ("I don't know if you come to me, and the moon is on my mind, my love " * 3, "en"),
        ("la la la", None),
    ],
)
def test_the_language_of_lyrics_is_guessed(text: str, language: str | None) -> None:
    assert guess_language(text) == language


async def test_without_a_key_the_sound_is_not_looked_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KARAOKE_ACOUSTID_KEY", raising=False)
    monkeypatch.setattr(identify, "probe_file", lambda path: (200.0, {}))
    monkeypatch.setattr(
        identify,
        "find_lyrics",
        lambda guess, duration: [{"id": 1, "text": "la", "source": "lrclib"}],
    )
    notes: list[tuple[str, str]] = []
    result = await identify.analyse(
        tmp_path / "song.webm",
        {"title": "Banda - Cantiga (Official Video)"},
        {},
        lambda step, line: notes.append((step, line)),
    )
    assert result["fingerprint"] == "no_key"
    assert result["best"]["title"] == "Cantiga"
    assert result["lyrics"][0]["id"] == 1
    assert [step for step, _ in notes][:2] == ["metadata", "fingerprint"]
    json.dumps(result)  # it goes to the server as JSON


def test_musicbrainz_is_asked_again_when_it_is_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identify.time, "sleep", lambda seconds: None)
    answers = iter([httpx.Response(503), httpx.Response(200, json={"releases": []})])
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return next(answers)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        identify.musicbrainz(client, Guess("acoustid", "Cantiga", recording="rec-1"))
    assert len(seen) == 2
    assert "inc=releases+artist-credits" in seen[0]
