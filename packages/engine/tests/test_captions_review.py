from karaoke_engine.captions.review import ReviewItem, format_review, review_items, timecode
from karaoke_engine.captions.rules import Caption, Rules, TimedWord


def cap(start: float, end: float, text: str, confidence: float = 0.9) -> Caption:
    words = tuple(
        TimedWord(w, start + i * 0.3, start + i * 0.3 + 0.25, confidence)
        for i, w in enumerate(text.split())
    )
    return Caption(start, end, (text,), (None,), words)


def test_timecode_at_25_and_29_97_fps() -> None:
    assert timecode(3725.52, 25.0) == "01:02:05:13"
    assert timecode(0.0, 25.0) == "00:00:00:00"
    assert timecode(60.0, 30000 / 1001) == "00:00:59:28"


def test_only_strong_signals_are_listed() -> None:
    fine = cap(1.0, 3.0, "Nacín aquí mesmo")
    doubtful = cap(4.0, 6.0, "Era en Carnota", confidence=0.1)
    items = review_items([fine, doubtful], Rules(), low_confidence=0.3)
    assert [item.start for item in items] == [4.0]
    assert items[0].reasons == ("palabra dudosa: «Era», «en», «Carnota»",)


def test_fast_reading_is_listed() -> None:
    fast = cap(1.0, 2.0, "Daquela isto era todo casas baixas e o porto")
    [item] = review_items([fast], Rules(), low_confidence=0.3)
    assert item.reasons == ("lectura rápida: 44 car./s",)


def test_reasons_of_one_caption_are_merged_into_one_item() -> None:
    caption = cap(1.0, 2.0, "Daquela isto era todo casas baixas e o porto", confidence=0.1)
    items = review_items([caption], Rules(), low_confidence=0.3, unsure_speaker=[1.5])
    assert len(items) == 1
    assert len(items[0].reasons) == 3
    assert items[0].reasons[-1] == "¿quién habla?"


def test_missed_speech_and_dropped_text_are_listed_in_time_order() -> None:
    items = review_items(
        [cap(10.0, 12.0, "Nacín aquí")],
        Rules(),
        low_confidence=0.3,
        missed=[(20.0, 24.5)],
        dropped=[(5.0, 6.0, "Subtítulos realizados por la comunidad de Amara.org")],
    )
    assert items == [
        ReviewItem(5.0, "Subtítulos realizados por la comunidad de Amara.org",
                   ("texto descartado",)),
        ReviewItem(20.0, "", ("voz sin texto (4.5 s)",)),
    ]  # fmt: skip


def test_format_review_has_a_summary_and_one_line_per_item() -> None:
    items = [ReviewItem(62.52, "Nacín en Carnota", ("palabra dudosa: «Carnota»",))]
    text = format_review(items, video="MVI_0704.MP4", captions=812, fps=25.0, elapsed=843.0)
    lines = text.splitlines()
    assert "MVI_0704.MP4" in lines[0]
    assert "812 subtítulos" in text
    assert "1 para mirar" in text
    assert "00:00:00:00" in text  # how to set the DaVinci timeline
    assert lines[-1] == "00:01:02:13  (62.5 s)  palabra dudosa: «Carnota»  «Nacín en Carnota»"


def test_format_review_without_items_says_so() -> None:
    text = format_review([], video="v.mp4", captions=3, fps=25.0, elapsed=1.0)
    assert "0 para mirar" in text
