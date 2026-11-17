from collections.abc import Callable
from pathlib import Path

import pytest

from karaoke_bench.cli import main
from karaoke_bench.lrc import parse_lrc, reference_from_lrc
from karaoke_bench.metrics import pair_scored, timing_errors, timing_stats
from karaoke_bench.reference import Reference, load_reference
from karaoke_contracts import Word

LRC = """[ar: Someone]
[00:12.50] Vou cantar
[00:15.08]mañá, de noite
[00:20.00]
[01:02.345] Vou cantar
"""


def _reference(text: str, duration: float = 70.0) -> Reference:
    return reference_from_lrc(parse_lrc(text), "song", "gl", duration)


def test_parse_lrc_reads_times_and_text() -> None:
    entries = parse_lrc(LRC)

    assert [(entry.start, entry.text) for entry in entries] == [
        (12.5, "Vou cantar"),
        (15.08, "mañá, de noite"),
        (20.0, ""),
        (62.345, "Vou cantar"),
    ]


def test_parse_lrc_repeats_a_line_written_with_several_times() -> None:
    entries = parse_lrc("[00:30.00][00:10.00] Ai la la\n[00:20.00] outra\n")

    assert [(entry.start, entry.text) for entry in entries] == [
        (10.0, "Ai la la"),
        (20.0, "outra"),
        (30.0, "Ai la la"),
    ]


def test_parse_lrc_reads_windows_line_endings() -> None:
    assert len(parse_lrc(LRC.replace("\n", "\r\n"))) == 4


def test_lines_end_where_the_next_entry_starts() -> None:
    ref = _reference(LRC)

    assert [line.text for line in ref.lines] == ["Vou cantar", "mañá, de noite", "Vou cantar"]
    # An entry without text only closes the line before it; the last line runs to the end.
    assert [(line.start, line.end) for line in ref.lines] == [
        (12.5, 15.08),
        (15.08, 20.0),
        (62.345, 70.0),
    ]


def test_reference_is_timed_by_lines_and_scores_their_first_word() -> None:
    ref = _reference(LRC)

    assert ref.timing == "lines"
    assert ref.approved
    assert [word.text for word in ref.scored_words()] == ["Vou", "mañá,", "Vou"]
    assert [word.start for word in ref.scored_words()] == [12.5, 15.08, 62.345]
    assert ref.lyrics_text() == "Vou cantar\nmañá, de noite\nVou cantar"


def test_a_line_without_words_is_not_a_line() -> None:
    ref = _reference("[00:01.00] ♪\n[00:05.00] ola\n", 9.0)

    assert [line.text for line in ref.lines] == ["ola"]


def test_no_timed_lines_is_an_error() -> None:
    with pytest.raises(ValueError, match="no timed lines"):
        _reference("Vou cantar\nmañá\n")


def test_only_line_starts_count_and_ends_do_not() -> None:
    ref = _reference("[00:01.00] ola meu mar\n[00:05.00] meu ben\n", 9.0)
    starts = [("ola", 1.1), ("meu", 3.0), ("mar", 3.5), ("meu", 5.4), ("ben", 6.0)]
    sung = [Word(text=text, start=start, end=start + 0.2) for text, start in starts]
    everything = [word for line in ref.lines for word in line.words]
    scored = ref.scored_words()

    errors = timing_errors(pair_scored(everything, scored, sung), len(scored), ends=False)

    assert errors.start == pytest.approx([0.1, 0.4])
    assert errors.end == []
    stats = timing_stats([errors])
    assert stats is not None
    assert stats.start_within == pytest.approx(0.5)
    assert stats.end_median is None
    assert stats.end_mean is None


@pytest.mark.usefixtures("ffmpeg")
def test_import_lrc_writes_the_private_reference(
    tmp_path: Path, make_tone: Callable[..., Path]
) -> None:
    song = tmp_path / "data" / "private" / "song"
    make_tone("data/private/song/audio.wav", 70.0)
    (song / "meta.toml").write_text('title = "Song"\nlanguage = "gl"\n', encoding="utf-8")
    lrc = tmp_path / "song.lrc"
    lrc.write_text(LRC, encoding="utf-8")

    code = main(["--bench-dir", str(tmp_path), "import-lrc", "private/song", str(lrc)])

    assert code == 0
    ref = load_reference(song / "reference.json")
    assert ref.timing == "lines"
    assert [line.text for line in ref.lines] == ["Vou cantar", "mañá, de noite", "Vou cantar"]
    assert ref.duration == pytest.approx(70.0, abs=0.01)


def test_import_lrc_refuses_public_sets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lrc = tmp_path / "song.lrc"
    lrc.write_text(LRC, encoding="utf-8")

    code = main(["--bench-dir", str(tmp_path), "import-lrc", "gl/song", str(lrc)])

    assert code == 1
    assert "private" in capsys.readouterr().err
