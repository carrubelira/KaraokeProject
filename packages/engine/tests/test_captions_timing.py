import itertools

import pytest

from karaoke_engine.captions.rules import Caption, Rules, TimedWord
from karaoke_engine.captions.timing import cps, time_captions

FPS = 25.0
FRAME = 1 / FPS


def cap(start: float, end: float, text: str = "Era o mar", speaker: str | None = None) -> Caption:
    """A caption whose words run from `start` to `end`."""
    word = TimedWord(text, start, end, 0.9, speaker)
    return Caption(start, end, (text,), (speaker,), (word,))


def timed(*captions: Caption, shots: tuple[float, ...] = (), duration: float | None = None):
    return time_captions(list(captions), Rules(), FPS, shots, duration)


def test_times_are_on_the_frame_grid() -> None:
    out = timed(cap(1.013, 2.371), cap(4.517, 5.0), cap(5.9, 8.33))
    for caption in out:
        for t in (caption.start, caption.end):
            assert t * FPS == pytest.approx(round(t * FPS), abs=1e-6)


def test_out_lingers_half_a_second_without_touching_the_next() -> None:
    # Half a second is 12.5 frames at 25 fps: the caption stays 12 (0.48 s).
    far = timed(cap(9.0, 10.0), cap(12.0, 13.0))
    assert far[0].end == pytest.approx(10.48)
    close = timed(cap(9.0, 10.0), cap(10.32, 11.0))
    assert close[0].end == pytest.approx(10.32 - 2 * FRAME)


def test_short_gaps_are_closed_to_two_frames() -> None:
    # Lingering would leave 0.4 s before the next caption: it closes to two frames instead.
    out = timed(cap(9.0, 10.0), cap(10.88, 12.0))
    assert out[1].start - out[0].end == pytest.approx(2 * FRAME)


def test_min_duration_is_reached_by_extending_the_end() -> None:
    [out] = timed(cap(5.0, 5.3, "Si"))
    assert out.start == pytest.approx(5.0)
    assert out.end - out.start >= 5 / 6


def test_min_duration_moves_the_start_back_when_the_next_is_close() -> None:
    out = timed(cap(5.0, 5.3, "Si"), cap(5.6, 7.0))
    assert out[0].end - out[0].start >= 5 / 6
    assert out[1].start - out[0].end >= 2 * FRAME - 1e-9


def test_start_snaps_to_a_nearby_cut() -> None:
    [out] = timed(cap(10.2, 12.0), shots=(10.0,))
    assert out.start == pytest.approx(10.0)


def test_end_snaps_back_before_a_nearby_cut() -> None:
    [out] = timed(cap(18.0, 20.0), shots=(20.32,))
    assert out.end == pytest.approx(20.32 - 2 * FRAME)


def test_far_cuts_are_ignored() -> None:
    [out] = timed(cap(10.2, 12.0), shots=(11.2, 13.5))
    assert out.start == pytest.approx(10.2)
    assert out.end == pytest.approx(12.48)


def test_a_cut_in_the_middle_of_speech_does_not_cut_it_short() -> None:
    # Ending two frames before this cut would hide the last word before it is said.
    [out] = timed(cap(18.0, 20.0), shots=(20.04,))
    assert out.end >= 20.0


def test_output_is_monotonic_and_never_overlaps() -> None:
    # Two people talking at once: their words overlap in time.
    out = timed(
        cap(0.0, 3.0, "Non, iso foi despois", "A"),
        cap(2.0, 4.0, "¿Despois de que?", "B"),
        cap(2.5, 3.5, "Da guerra", "A"),
        cap(6.0, 7.0, "Ah", "B"),
    )
    for previous, caption in itertools.pairwise(out):
        assert caption.start >= previous.end + 2 * FRAME - 1e-9
    assert all(c.end > c.start for c in out)


def test_never_ends_after_the_video() -> None:
    [out] = timed(cap(8.0, 9.9), duration=10.0)
    assert out.end <= 10.0


def test_text_and_speakers_are_kept() -> None:
    [out] = timed(cap(1.0, 2.0, "Era o mar", "A"))
    assert out.lines == ("Era o mar",)
    assert out.speakers == ("A",)


def test_cps_counts_characters_per_second() -> None:
    caption = Caption(0.0, 2.0, ("Era o mar,", "e o porto."), (None, None))
    assert cps(caption) == pytest.approx(len("Era o mar,e o porto.") / 2.0)


def test_a_gap_left_by_the_minimum_duration_is_closed_too() -> None:
    # "Chegaron" lasts 0.2 s; made readable it ends 0.36 s before the next caption: chained.
    out = timed(cap(5.0, 5.2, "Chegaron"), cap(6.2, 8.0))
    assert out[1].start - out[0].end == pytest.approx(2 * FRAME)


def test_a_fast_caption_stays_long_enough_to_read_when_there_is_room() -> None:
    text = "Daquela era todo casas baixas e o porto"  # 39 characters said in one second
    [fast, _] = timed(cap(1.0, 2.0, text), cap(6.0, 7.0))
    assert fast.end - fast.start >= len(text) / 15 - FRAME
    assert fast.end <= 6.0 - 2 * FRAME


def test_a_fast_caption_never_runs_into_the_next() -> None:
    text = "Daquela era todo casas baixas e o porto"
    out = timed(cap(1.0, 2.0, text), cap(3.0, 4.0))
    assert out[0].end == pytest.approx(3.0 - 2 * FRAME)
