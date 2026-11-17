import json

import pytest

from karaoke_engine.lyrics_lookup import find_lyrics


def _entry(i: int, duration: float, plain: str | None = "Ola\nmar") -> dict[str, object]:
    return {"id": i, "trackName": "Canción", "artistName": "Grupo", "duration": duration,
            "plainLyrics": plain, "syncedLyrics": None}  # fmt: skip


class FakeWeb:
    def __init__(self, *answers: tuple[int, object]) -> None:
        self.answers = list(answers)
        self.urls: list[str] = []

    def __call__(self, url: str) -> tuple[int, bytes]:
        self.urls.append(url)
        status, body = self.answers.pop(0)
        return status, json.dumps(body).encode()


def test_closest_duration_wins() -> None:
    web = FakeWeb((200, [_entry(1, 200.0), _entry(2, 181.0), _entry(3, 179.5, None)]))

    found = find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert found.source_id == 2
    assert found.text == "Ola\nmar"
    assert "track_name=Canci%C3%B3n" in web.urls[0]


def test_retries_when_the_server_is_busy() -> None:
    web = FakeWeb((503, {"message": "busy"}), (200, [_entry(1, 180.0)]))

    found = find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert len(web.urls) == 2


def test_nothing_close_in_duration_is_no_match() -> None:
    web = FakeWeb((200, [_entry(1, 240.0)]))

    assert find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None) is None


def test_gives_up_after_three_busy_answers() -> None:
    web = FakeWeb(*[(503, {})] * 3)

    with pytest.raises(OSError, match="busy"):
        find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)


def test_no_wait_after_the_last_attempt() -> None:
    waits: list[float] = []
    web = FakeWeb(*[(503, {})] * 3)

    with pytest.raises(OSError, match="busy"):
        find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=waits.append)

    assert len(waits) == 2


@pytest.mark.parametrize(
    ("title", "artist", "names"),
    [
        # How a video page names a song: the artist in front, what kind of video behind.
        ("The Rapants - Viaxei", "The Rapants", ["Viaxei"]),
        ("Kid Mount, Yuly - Esta Vida Pide Outra", "Kid Mount", ["Esta Vida Pide Outra"]),
        ("9Louro, Yuly, Ortiga - Veráns", "9Louro", ["Veráns"]),
        (
            "Fillas de Cassandra // II. LISÍSTRATA (varre vasoira) - Vídeo Oficial",
            "Fillas de Cassandra",
            ["II. LISÍSTRATA (varre vasoira)", "II. LISÍSTRATA"],
        ),
        ("Tanxugueiras - Terra (Official Video)", "Tanxugueiras", ["Terra"]),
        ("Terra | Tanxugueiras [Videoclip oficial]", "Tanxugueiras", ["Terra"]),
        ("Sés \u2013 Tempestades de sal ft. Outra Xente", "Sés", ["Tempestades de sal"]),
        # Nothing to take away: the title as it is, and without what is in brackets.
        ("Viaxei", "The Rapants", ["Viaxei"]),
        ("Miña terra (acústica)", "Alguén", ["Miña terra (acústica)", "Miña terra"]),
        # A hyphen inside a word is not a separator.
        ("Sen-ti-do", "Alguén", ["Sen-ti-do"]),
    ],
)
def test_song_names_from_a_video_title(title: str, artist: str, names: list[str]) -> None:
    from karaoke_engine.lyrics_lookup import song_names

    assert song_names(title, artist) == names


def test_a_video_title_is_asked_again_as_the_song_s_name() -> None:
    web = FakeWeb((200, []), (200, [_entry(7, 247.0)]))

    found = find_lyrics(
        "The Rapants - Viaxei", "The Rapants", 247.2, fetch=web, wait=lambda s: None
    )

    assert found is not None
    assert found.source_id == 7
    assert "track_name=The+Rapants+-+Viaxei" in web.urls[0]
    assert "track_name=Viaxei&" in web.urls[1] + "&"
    assert "artist_name=The+Rapants" in web.urls[1]


def test_the_same_question_is_not_asked_twice() -> None:
    web = FakeWeb((200, [_entry(1, 240.0)]))

    # The title is already the song's name, and the entry found is another edit: one question.
    assert find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None) is None
    assert len(web.urls) == 1


def test_a_free_search_is_the_last_resort() -> None:
    mine = {**_entry(3, 180.0), "artistName": "Grupo e Amigos"}
    other = {**_entry(4, 180.0), "artistName": "Outra Banda"}
    web = FakeWeb((200, []), (200, []), (200, [other, mine]))

    found = find_lyrics("Grupo - Canción (Official Video)", "Grupo", 180.0, fetch=web,
                        wait=lambda s: None)  # fmt: skip

    assert found is not None
    # Only an entry by the artist asked for: a free search also finds other people's songs.
    assert found.source_id == 3
    assert "q=Grupo+Canci%C3%B3n" in web.urls[2]


def test_a_video_longer_than_the_song_is_still_the_song() -> None:
    # The video of a song often opens with a spoken scene or ends with credits.
    web = FakeWeb((200, [_entry(1, 169.0), _entry(2, 138.0)]))

    found = find_lyrics("Canción", "Grupo", 208.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert found.source_id == 1


def test_the_same_edit_wins_over_a_shorter_one() -> None:
    web = FakeWeb((200, [_entry(1, 150.0), _entry(2, 182.0)]))

    found = find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None)

    assert found is not None
    assert found.source_id == 2


def test_an_entry_much_longer_than_the_audio_is_another_edit() -> None:
    web = FakeWeb((200, [_entry(1, 190.0)]))

    assert find_lyrics("Canción", "Grupo", 180.0, fetch=web, wait=lambda s: None) is None
