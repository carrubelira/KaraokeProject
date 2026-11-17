from karaoke_engine.captions.lines import break_lines
from karaoke_engine.captions.rules import FUNCTION_WORDS, Rules


def ws(text: str) -> list[str]:
    return text.split()


def test_one_line_when_it_fits() -> None:
    assert break_lines(ws("Nacín aquí mesmo"), Rules()) == ("Nacín aquí mesmo",)


def test_two_lines_never_end_on_a_function_word() -> None:
    words = ws("Daquela isto era todo casas baixas e o porto quedaba a dous pasos")
    lines = break_lines(words, Rules())
    assert lines is not None
    top, bottom = lines
    assert top.split()[-1].lower() not in FUNCTION_WORDS
    assert len(top) <= 42
    assert len(bottom) <= 42
    assert f"{top} {bottom}" == " ".join(words)


def test_prefers_breaking_after_punctuation() -> None:
    words = ws("Meu pai andaba no mar, como case todos os da rúa de arriba")
    lines = break_lines(words, Rules())
    assert lines is not None
    assert lines[0] == "Meu pai andaba no mar,"


def test_prefers_a_longer_bottom_line_when_balanced_otherwise() -> None:
    # Eleven equal words: one line takes five and the other six; the six go below.
    words = ["mareas"] * 11
    lines = break_lines(words, Rules())
    assert lines is not None
    top, bottom = lines
    assert len(top.split()) == 5
    assert len(bottom.split()) == 6


def test_none_when_it_does_not_fit_in_two_lines() -> None:
    assert break_lines(["palabra"] * 30, Rules()) is None


def test_a_word_longer_than_a_line_does_not_fit() -> None:
    assert break_lines(["x" * 43], Rules()) is None


def test_clitics_and_contractions_are_function_words() -> None:
    for word in ("o", "a", "do", "da", "no", "na", "polo", "coa", "que", "e", "lle", "non"):
        assert word in FUNCTION_WORDS
