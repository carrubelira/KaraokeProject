from karaoke_engine.captions.lines import break_lines
from karaoke_engine.captions.rules import Rules, TimedWord
from karaoke_engine.captions.segment import group_captions


def said(
    text: str,
    start: float = 0.0,
    speaker: str | None = None,
    pause_after: dict[int, float] | None = None,
) -> list[TimedWord]:
    """Words of 0.3 s with 0.1 s between them, and longer pauses after the given word indices."""
    words, t = [], start
    for i, token in enumerate(text.split()):
        words.append(TimedWord(token, round(t, 3), round(t + 0.3, 3), 0.9, speaker))
        t += 0.4 + (pause_after or {}).get(i, 0.0)
    return words


def texts(captions: list) -> list[str]:
    return [" ".join(c.lines) for c in captions]


def test_every_word_appears_once_in_order() -> None:
    words = said(" ".join(f"palabra{i}" + ("." if i % 17 == 16 else "") for i in range(300)))
    captions = group_captions(words, Rules())
    assert [w for c in captions for w in c.words] == words


def test_breaks_at_a_speaker_change() -> None:
    words = said("Onde naceu vostede", 0.0, "B") + said("Nacín aquí mesmo", 3.0, "A")
    captions = group_captions(words, Rules())
    assert texts(captions) == ["Onde naceu vostede", "Nacín aquí mesmo"]
    assert [c.speakers for c in captions] == [("B",), ("A",)]


def test_a_sentence_end_followed_by_a_pause_always_breaks() -> None:
    words = said("Era o mar. Despois veu a fábrica", pause_after={2: 0.4})
    assert texts(group_captions(words, Rules())) == ["Era o mar.", "Despois veu a fábrica"]


def test_breaks_at_sentence_end_before_pause_before_comma() -> None:
    # Too long for one caption: the sentence end wins over the later pause and the comma.
    text = (
        "Meu pai andaba no mar como case todos os veciños. Eu quedaba coa miña nai na casa, "
        "e axudabamos no que se podía porque non había moito diñeiro naquela época de fame"
    )
    words = said(text, pause_after={22: 0.4})
    captions = group_captions(words, Rules())
    assert texts(captions)[0] == "Meu pai andaba no mar como case todos os veciños."


def test_breaks_at_a_pause_before_a_comma() -> None:
    text = (
        "Eu quedaba coa miña nai na casa, axudabamos no que se podía porque non había "
        "moito diñeiro naquela época de fame e de traballo para todos os da rúa"
    )
    words = said(text, pause_after={11: 0.4})
    first = texts(group_captions(words, Rules()))[0]
    assert first.split()[-1] == "podía"


def test_never_exceeds_two_lines_or_max_duration() -> None:
    words = said(" ".join(["mareas", "e", "barcos,"] * 120))
    for caption in group_captions(words, Rules()):
        assert break_lines([w.text for w in caption.words], Rules()) is not None
        assert len(caption.lines) <= 2
        assert all(len(line) <= 42 for line in caption.lines)
        assert caption.end - caption.start <= 7.0


def test_a_caption_does_not_end_on_a_word_that_leans_forward() -> None:
    words = said(" ".join(["Daquela", "fomos", "todos", "ao", "porto", "de", "Lira"] * 12))
    for caption in group_captions(words, Rules())[:-1]:
        assert caption.words[-1].text.lower() not in {"ao", "de"}


def test_short_question_and_answer_share_a_caption_with_dashes() -> None:
    words = said("¿E logo?", 0.0, "B") + said("Pois si.", 1.1, "A")
    [caption] = group_captions(words, Rules())
    assert caption.lines == ("-¿E logo?", "-Pois si.")
    assert caption.speakers == ("B", "A")
    assert caption.start == 0.0
    assert caption.end == words[-1].end


def test_long_turns_are_not_merged_with_dashes() -> None:
    question = said("¿E como era a vida no porto cando vostede era pequena?", 0.0, "B")
    answer = said("Pois si.", question[-1].end + 0.3, "A")
    assert len(group_captions(question + answer, Rules())) == 2


def test_turns_far_apart_are_not_merged_with_dashes() -> None:
    words = said("¿E logo?", 0.0, "B") + said("Pois si.", 4.0, "A")
    assert len(group_captions(words, Rules())) == 2


def test_a_word_longer_than_a_line_is_a_caption_of_its_own() -> None:
    words = said("Antes " + "x" * 50 + " despois")
    assert texts(group_captions(words, Rules())) == ["Antes", "x" * 50, "despois"]


def test_no_words_no_captions() -> None:
    assert group_captions([], Rules()) == []


def test_a_lone_short_word_is_not_cut_off_at_a_pause() -> None:
    text = "Chegaron cando xa estabamos todos no peirao de abaixo, e ninguén os esperaba aquel día"
    captions = group_captions(said(text, pause_after={0: 1.0}), Rules())
    assert texts(captions)[0] != "Chegaron"


def test_a_caption_that_only_fits_with_a_dangling_break_is_cut_sooner() -> None:
    text = "despois que xa colleu unha rede, unha rede de malla fina, e levouna ao porto, e máis"
    for caption in group_captions(said(text), Rules()):
        if len(caption.lines) == 2:
            assert caption.lines[0].split()[-1] not in {"unha", "a", "de", "e"}


def test_a_word_with_no_time_to_be_read_joins_the_next_caption_as_dialogue() -> None:
    before = said("Non me lembro de máis.", 0.0, "A")
    claro = said("Claro,", before[-1].end + 1.5, "B")
    after = said("Chegaron ao peirao.", claro[-1].end + 0.05, "A")
    captions = group_captions(before + claro + after, Rules())
    assert [c.lines for c in captions][-1] == ("-Claro,", "-Chegaron ao peirao.")
    assert captions[-1].speakers == ("B", "A")


def test_a_word_with_no_time_to_be_read_joins_the_next_caption_of_its_speaker() -> None:
    aqui = said("Aquí.", 0.0, "A")
    rest = said("Estaba o porto de Lira.", aqui[-1].end + 0.35, "A")
    captions = group_captions(aqui + rest, Rules())
    assert [" ".join(c.lines) for c in captions] == ["Aquí. Estaba o porto de Lira."]
