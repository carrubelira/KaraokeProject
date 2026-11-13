import pytest

from karaoke_engine.captions.formats import read_srt, to_srt, to_vtt
from karaoke_engine.captions.rules import Caption

LABELS = {"A": "Entrevistado", "B": "Entrevistador"}


def cap(start: float, end: float, *lines: str, speakers: tuple[str | None, ...] = ()) -> Caption:
    return Caption(start, end, tuple(lines), speakers or (None,) * len(lines))


def test_srt_timecodes_past_one_hour() -> None:
    text = to_srt([cap(3725.5, 3727.04, "Cando volvín")])
    assert "01:02:05,500 --> 01:02:07,040" in text


def test_srt_numbers_cues_and_uses_crlf() -> None:
    text = to_srt([cap(1.0, 2.0, "Un"), cap(3.0, 4.0, "Dous")])
    assert text == (
        "1\r\n00:00:01,000 --> 00:00:02,000\r\nUn\r\n\r\n"
        "2\r\n00:00:03,000 --> 00:00:04,000\r\nDous\r\n\r\n"
    )


def test_srt_round_trip_keeps_text_and_times() -> None:
    captions = [
        cap(0.04, 1.2, "Nacín na rúa de arriba,", "onde a señora Pilar."),
        cap(1.28, 2.6, "-¿E logo?", "-Pois si, ñoño."),
    ]
    back = read_srt(to_srt(captions))
    assert [(c.start, c.end, c.lines) for c in back] == [
        (c.start, c.end, c.lines) for c in captions
    ]


def test_read_srt_accepts_bom_crlf_and_davinci_numbering() -> None:
    text = (
        "﻿7\r\n00:00:01,000 --> 00:00:02,500  \r\nOla\r\n\r\n\r\n"
        "00:00:03.000 --> 00:00:04.000\r\n<i>Que tal</i>\r\n\r\n"
    )
    back = read_srt(text)
    assert [(c.start, c.end, c.lines) for c in back] == [
        (1.0, 2.5, ("Ola",)),
        (3.0, 4.0, ("Que tal",)),
    ]
    assert back[0].speakers == (None,)


def test_read_srt_rejects_text_without_cues() -> None:
    with pytest.raises(ValueError, match="no subtitles"):
        read_srt("isto non é un srt")


def test_vtt_has_header_note_and_voice_tags() -> None:
    text = to_vtt(
        [cap(1.0, 2.5, "Nacín aquí", "mesmo.", speakers=("A", "A"))],
        "Automatic, not reviewed.",
        LABELS,
    )
    assert text.startswith("WEBVTT\n\nNOTE\nAutomatic, not reviewed.\n\n")
    assert "00:00:01.000 --> 00:00:02.500\n<v Entrevistado>Nacín aquí\nmesmo.\n" in text


def test_vtt_dialogue_has_a_voice_per_line() -> None:
    text = to_vtt([cap(1.0, 2.0, "-¿E logo?", "-Pois si.", speakers=("B", "A"))], "", LABELS)
    assert "<v Entrevistador>-¿E logo?</v>\n<v Entrevistado>-Pois si.</v>" in text


def test_vtt_without_speakers_has_no_voice_tags() -> None:
    text = to_vtt([cap(1.0, 2.0, "Ola")], "", LABELS)
    assert "<v" not in text


def test_vtt_escapes_angle_brackets_and_ampersands() -> None:
    text = to_vtt([cap(1.0, 2.0, "Pan & viño <ben>")], "a --> b", LABELS)
    assert "Pan &amp; viño &lt;ben&gt;" in text
    assert "a --> b" not in text  # a NOTE may not contain the cue arrow
