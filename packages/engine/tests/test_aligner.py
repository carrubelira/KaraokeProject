import math
import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.aligner import LyricsAligner
from karaoke_engine.align.emissions import Emissions, Vocab, compact
from karaoke_engine.steps import Aligner, TextAligner

RATE = 16000
HOP = 0.02
ALPHABET = "abcdefghijklmnopqrstuvwxyzñ"
pytestmark = pytest.mark.usefixtures("ffmpeg")


class ScriptedModel:
    """Emissions where each listed letter peaks at its frame and the blank wins elsewhere."""

    def __init__(self, peaks: Sequence[tuple[str, int]]) -> None:
        mapping = {"<pad>": 0, "|": 1, **{ch: i + 2 for i, ch in enumerate(ALPHABET)}}
        self.vocab = Vocab.from_mapping(mapping, blank=0, fallbacks={})
        self.peaks = list(peaks)

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def emissions(self, samples: np.ndarray, ids: Sequence[int]) -> Emissions:
        frames = len(samples) // round(HOP * RATE)
        lp = np.full((frames, len(ALPHABET) + 2), -8.0, dtype=np.float32)
        lp[:, 0] = -0.01
        for ch, frame in self.peaks:
            lp[frame, :] = -8.0
            lp[frame, self.vocab.ids[ch]] = -0.01
        return Emissions(compact(lp, 0, ids), HOP)


def _vocals(tmp_path: Path, voiced: Sequence[tuple[float, float]], seconds: float = 6.0) -> Path:
    samples = np.zeros(round(seconds * RATE), dtype=np.float32)
    t = np.arange(len(samples)) / RATE
    for start, end in voiced:
        inside = (t >= start) & (t < end)
        samples[inside] = 0.5 * np.sin(2 * np.pi * 220 * t[inside])
    path = tmp_path / "vocals.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def _spell(text: str, first: int, step: int = 3) -> list[tuple[str, int]]:
    letters = [ch for ch in text if ch.isalpha()]
    return [(ch, first + i * step) for i, ch in enumerate(letters)]


def _aligner(peaks: Sequence[tuple[str, int]], **params: object) -> LyricsAligner:
    return LyricsAligner(emission_model=ScriptedModel(peaks), **params)  # type: ignore[arg-type]


def test_lyrics_aligner_is_both_kinds_of_aligner() -> None:
    aligner = LyricsAligner(emission_model=ScriptedModel([]))

    assert isinstance(aligner, Aligner)
    assert isinstance(aligner, TextAligner)


def test_align_text_returns_words_in_order(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 150)

    lines = _aligner(peaks).align_text(vocals, "Ola, mar\nVai vento\n", "gl")

    assert [[w.text for w in line.words] for line in lines] == [["Ola,", "mar"], ["Vai", "vento"]]
    assert lines[0].words[0].start == pytest.approx(20 * HOP)
    assert lines[1].words[0].start == pytest.approx(150 * HOP)
    assert lines[1].start == lines[1].words[0].start
    assert all(0.5 < (w.confidence or 0) <= 1 for line in lines for w in line.words)


def test_unsung_line_is_left_out(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("adeus", 200)

    aligner = _aligner(peaks, edge_skip_penalty=math.inf)
    lines = aligner.align_text(vocals, "ola mar\nnunca se canta isto\nadeus\n", "gl")

    assert [line.words[0].text for line in lines] == ["ola", "adeus"]


def test_backing_line_is_marked(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("mar", 80)

    lines = _aligner(peaks).align_text(vocals, "ola (mar)\n", "gl")

    assert [line.role for line in lines] == ["lead", "backing"]


def test_words_without_tokens_get_neighbour_times(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("adeus", 60)

    [line] = _aligner(peaks).align_text(vocals, "ola 123 adeus\n", "de")

    ola, number, adeus = line.words
    assert number.start == number.end == ola.end
    assert number.confidence == 0.0
    assert adeus.start == pytest.approx(60 * HOP)


def test_onset_refinement_moves_line_start_to_voice_onset(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(1.0, 3.0)])
    peaks = _spell("ola", 60)

    [refined] = _aligner(peaks, refine_onsets=True).align_text(vocals, "ola\n", "gl")
    [plain] = _aligner(peaks).align_text(vocals, "ola\n", "gl")

    assert refined.start == pytest.approx(1.0, abs=HOP)
    assert plain.start == pytest.approx(1.2, abs=HOP)


def test_word_end_is_trimmed_to_voice(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 2.0)])
    peaks = [*_spell("ol", 20), *(("a", f) for f in range(40, 131))]

    [line] = _aligner(peaks, silence_penalty=0.0).align_text(vocals, "ola\n", "gl")

    assert line.words[0].end <= 2.1 + HOP


def test_align_matches_align_text_for_plain_lines(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 150)
    aligner = _aligner(peaks)

    assert aligner.align(vocals, ["ola mar", "vai vento"], "gl") == aligner.align_text(
        vocals, "ola mar\nvai vento", "gl"
    )


def test_onset_refinement_applies_after_a_pause_inside_a_line(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.4, 1.0), (2.4, 3.0)])
    peaks = _spell("ola", 20) + _spell("mar", 130)

    [line] = _aligner(peaks, refine_onsets=True).align_text(vocals, "ola mar\n", "gl")

    assert line.words[1].start == pytest.approx(2.4, abs=HOP)


def test_word_end_stops_at_the_first_long_silence(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 1.0), (3.0, 4.0)])
    peaks = [*_spell("ol", 20), *(("a", f) for f in range(40, 176))]

    [line] = _aligner(peaks, silence_penalty=0.0).align_text(vocals, "ola\n", "gl")

    assert line.words[0].end <= 1.1 + HOP


def test_lyrics_longer_than_the_song_keep_the_lines_that_are_sung(tmp_path: Path) -> None:
    # A clip of a song with the whole song's lyrics: the first lines are sung, the rest is not,
    # and many short lines must not be crammed in instead.
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("primeira longa", 20) + _spell("segunda longa", 120)
    lyrics = "primeira longa\nsegunda longa\n" + "pa pan\n" * 20

    lines = _aligner(peaks).align_text(vocals, lyrics, "gl")

    assert [" ".join(w.text for w in line.words) for line in lines][:2] == [
        "primeira longa",
        "segunda longa",
    ]


def test_parts_follow_letter_times(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = [("c", 20), ("a", 24), ("m", 40), ("i", 44), ("ñ", 60), ("a", 64), ("n", 66),
             ("d", 80), ("o", 84)]  # fmt: skip

    [line] = _aligner(peaks).align_text(vocals, "camiñando\n", "gl")

    parts = line.words[0].parts
    assert [p.text for p in parts] == ["ca", "mi", "ñan", "do"]
    assert [p.start for p in parts] == pytest.approx([20 * HOP, 40 * HOP, 60 * HOP, 80 * HOP])
    assert parts[-1].end == line.words[0].end


def test_parts_skip_words_whose_letters_do_not_map(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("dous mil vinte", 20)

    [line] = _aligner(peaks).align_text(vocals, "2020\n", "gl")

    assert line.words[0].parts == []


def test_model_for_language_names_the_pinned_model() -> None:
    aligner = LyricsAligner()

    assert aligner.model_for_language("gl").startswith(
        "proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl@"
    )
    # A language without a model of its own: the one trained on songs, until lyrics say otherwise.
    assert aligner.model_for_language("eu").startswith("mrfakename/w2v-bert-2.0-music-lyrics-ctc@")


def test_header_singer_reaches_the_line(tmp_path: Path) -> None:
    from karaoke_engine.align.lyrics import singer_id

    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola", 20) + _spell("mar", 120)

    lines = _aligner(peaks).align_text(
        vocals, "[Verso: Ana]\nola\n[Estribillo: Brais]\nmar\n", "gl"
    )

    assert [line.singer for line in lines] == [singer_id("Ana"), singer_id("Brais")]


def test_backing_line_overlapping_the_lead_is_placed(tmp_path: Path) -> None:
    # The backing part is written after the lead line but sung in the middle of it.
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = [("o", 20), ("l", 23), ("a", 26), ("v", 30), ("i", 33),
             ("m", 40), ("a", 43), ("r", 46)]  # fmt: skip

    lines = _aligner(peaks, overlap_backing=True).align_text(vocals, "ola mar (vi)\n", "gl")

    lead, backing = lines
    assert (lead.role, backing.role) == ("lead", "backing")
    assert [w.start for w in lead.words] == pytest.approx([20 * HOP, 40 * HOP])
    assert backing.start == pytest.approx(30 * HOP)
    assert backing.start < lead.end


def test_unsung_backing_line_is_left_out(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20)

    lines = _aligner(peaks, overlap_backing=True).align_text(vocals, "ola mar (yeah)\n", "gl")

    assert [line.role for line in lines] == ["lead"]


def test_parts_skip_words_with_a_letter_the_model_lacks(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("sla", 20)

    [line] = _aligner(peaks).align_text(vocals, "søla\n", "gl")

    assert line.words[0].parts == []


def _texts(lines: Sequence[object]) -> list[str]:
    return [" ".join(w.text for w in line.words) for line in lines]  # type: ignore[attr-defined]


def test_a_couplet_written_once_and_sung_twice_shows_each_time(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = []
    for start in (20, 140):
        peaks += _spell("ola mar", start) + _spell("vai vento", start + 50)

    lines = _aligner(peaks, repeat_penalty=20.0).align_text(vocals, "Ola mar\nVai vento\n", "gl")

    assert _texts(lines) == ["Ola mar", "Vai vento", "Ola mar", "Vai vento"]
    assert [line.start for line in lines] == pytest.approx([0.4, 1.4, 2.8, 3.8])
    assert len({line.id for line in lines}) == 4


def test_the_audio_chooses_what_a_repeat_mark_covers(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 8.0)], seconds=8.0)
    peaks = []
    for start in (20, 140):
        peaks += _spell("ola mar", start) + _spell("vai vento", start + 50)
    peaks += _spell("adeus", 260)
    text = "Ola mar\nVai vento (x2)\nAdeus\n"

    lines = _aligner(peaks, repeat_penalty=math.inf).align_text(vocals, text, "gl")

    assert _texts(lines) == ["Ola mar", "Vai vento", "Ola mar", "Vai vento", "Adeus"]


def test_a_repeat_mark_over_one_line_keeps_that_reading(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 70) + _spell("vai vento", 120)
    text = "Ola mar\nVai vento (x2)\n"

    lines = _aligner(peaks, repeat_penalty=math.inf).align_text(vocals, text, "gl")

    assert _texts(lines) == ["Ola mar", "Vai vento", "Vai vento"]


def test_a_second_model_hears_the_line_the_first_one_misses(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    first = ScriptedModel(_spell("ola mar", 20))
    second = ScriptedModel(_spell("vai vento", 150))
    lyrics = "Ola mar\nVai vento\n"

    alone = LyricsAligner(emission_model=first).align_text(vocals, lyrics, "gl")
    both = LyricsAligner(emission_model=first, second_emission_model=second).align_text(
        vocals, lyrics, "gl"
    )

    assert [line.words[0].text for line in alone] == ["Ola"]
    assert [line.words[0].text for line in both] == ["Ola", "Vai"]
    assert both[0].words[0].start == pytest.approx(20 * HOP)
    assert both[1].words[0].start == pytest.approx(150 * HOP)


def test_a_second_model_with_no_weight_changes_nothing(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = _spell("ola mar", 20) + _spell("vai vento", 150)
    lyrics = "Ola mar\nVai vento\n"

    alone = _aligner(peaks).align_text(vocals, lyrics, "gl")
    both = LyricsAligner(
        emission_model=ScriptedModel(peaks),
        second_emission_model=ScriptedModel(_spell("vai vento", 30)),
        second_weight=0.0,
    ).align_text(vocals, lyrics, "gl")

    assert both == alone


class OtherRateModel(ScriptedModel):
    """A model with frames of 40 ms: half as many as the first one's."""

    def emissions(self, samples: np.ndarray, ids: Sequence[int]) -> Emissions:
        every = super().emissions(samples, ids)
        return Emissions(every.log_probs[::2], HOP * 2)


def test_models_with_different_frame_rates_are_blended_in_time(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    # Peaks on even frames, so the slower model keeps them: its frame 75 is the second 3.0.
    second = OtherRateModel(_spell("vai vento", 150, step=4))

    lines = LyricsAligner(
        emission_model=ScriptedModel(_spell("ola mar", 20)), second_emission_model=second
    ).align_text(vocals, "Ola mar\nVai vento\n", "gl")

    assert [line.words[0].text for line in lines] == ["Ola", "Vai"]
    assert lines[1].words[0].start == pytest.approx(150 * HOP, abs=1.5 * HOP)


def test_a_letter_only_the_second_model_knows_is_still_aligned(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    first = ScriptedModel(_spell("ola", 20))
    second = ScriptedModel([("o", 20), ("l", 23), ("a", 26), ("ß", 29)])
    second.vocab = Vocab.from_mapping({**second.vocab.ids, "ß": len(ALPHABET) + 2}, 0, {})

    def emissions(samples: np.ndarray, ids: Sequence[int]) -> Emissions:
        frames = len(samples) // round(HOP * RATE)
        lp = np.full((frames, len(ALPHABET) + 3), -8.0, dtype=np.float32)
        lp[:, 0] = -0.01
        for ch, frame in second.peaks:
            lp[frame, :] = -8.0
            lp[frame, second.vocab.ids[ch]] = -0.01
        return Emissions(compact(lp, 0, ids), HOP)

    second.emissions = emissions  # type: ignore[method-assign]

    [line] = LyricsAligner(emission_model=first, second_emission_model=second).align_text(
        vocals, "olaß\n", "de"
    )

    [word] = line.words
    assert word.start == pytest.approx(20 * HOP)
    # The word runs to the letter only the second model placed.
    assert word.end >= 29 * HOP


def test_provenance_names_both_models() -> None:
    aligner = LyricsAligner(second="music-w2vbert-ctc")

    name = aligner.model_for_language("gl")

    assert "Nos_ASR-wav2vec2-xls-r-300m-gl@" in name
    assert "w2v-bert-2.0-music-lyrics-ctc@" in name
    # A language whose own model is already the second one uses it once.
    assert (
        LyricsAligner(model="music-w2vbert-ctc", second="music-w2vbert-ctc")
        .model_for_language("gl")
        .count("@")
        == 1
    )


class CountingModel(ScriptedModel):
    def __init__(self, peaks: Sequence[tuple[str, int]]) -> None:
        super().__init__(peaks)
        self.unloads = 0

    def unload(self) -> None:
        self.unloads += 1


def test_two_models_take_turns_on_the_gpu(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    first = CountingModel(_spell("ola mar", 20))
    second = CountingModel(_spell("vai vento", 150))

    LyricsAligner(emission_model=first, second_emission_model=second).align_text(
        vocals, "Ola mar\nVai vento\n", "gl"
    )

    # Each one leaves the card before the other loads: a 4 GB card holds one at a time.
    assert (first.unloads, second.unloads) == (1, 1)


def test_a_single_model_stays_loaded_for_the_next_song(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    model = CountingModel(_spell("ola mar", 20))

    LyricsAligner(emission_model=model).align_text(vocals, "Ola mar\n", "gl")

    assert model.unloads == 0


def test_a_one_letter_word_stays_with_its_line(tmp_path: Path) -> None:
    # "A avoa": something like an "a" sounds in the intro, 3 s before the line is sung.
    vocals = _vocals(tmp_path, [(0.2, 0.6), (3.8, 6.0)])
    peaks = [("a", 20), *_spell("avoa", 200)]
    lyrics = "A avoa\n"

    [free] = _aligner(peaks).align_text(vocals, lyrics, "gl")
    [kept] = _aligner(peaks, rest_penalty=0.1).align_text(vocals, lyrics, "gl")

    assert free.start == pytest.approx(20 * HOP)
    assert kept.start > 3.5
    assert kept.words[1].start == pytest.approx(200 * HOP)


def _vocab(letters: str) -> Vocab:
    return Vocab.from_mapping(
        {"<pad>": 0, "|": 1, **{ch: i + 2 for i, ch in enumerate(letters)}}, 0, {}
    )


def _fallback_with(
    monkeypatch: pytest.MonkeyPatch, letters: str, lyrics: str, language: str
) -> str:
    from karaoke_engine.align import aligner as module
    from karaoke_engine.align.lyrics import parse_lyrics

    monkeypatch.setattr(module, "_vocab_of", lambda name: _vocab(letters))
    return LyricsAligner()._names_for(language, parse_lyrics(lyrics))[0]


def test_a_language_without_a_model_uses_the_music_model(monkeypatch: pytest.MonkeyPatch) -> None:
    name = _fallback_with(monkeypatch, ALPHABET + "àèìòù", "Volare, oh oh\nCantare\n", "it")

    assert name == "music-w2vbert-ctc"


def test_lyrics_the_music_model_cannot_write_go_to_the_wide_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = _fallback_with(monkeypatch, ALPHABET, "तुम ही हो\nअब तुम ही हो\n", "hi")

    assert name == "omni-ctc-300m"


def test_a_few_foreign_letters_do_not_change_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    lyrics = "Volare, oh oh, cantare, nel blu dipinto di blu\nfelice di stare lassù 東\n"

    assert _fallback_with(monkeypatch, ALPHABET + "ù", lyrics, "it") == "music-w2vbert-ctc"


def test_a_language_with_its_own_model_keeps_it() -> None:
    # Its own model first; the music model joins it as the second listener.
    assert LyricsAligner()._names_for("gl") == ("nos-xlsr-300m-gl", "music-w2vbert-ctc")


def test_a_syllable_block_is_spelled_with_its_letters(tmp_path: Path) -> None:
    # The music model writes Korean with the letters of each block (jamo), not whole blocks.
    jamo = "한"  # the three parts of 한
    model = ScriptedModel([])
    model.vocab = _vocab(ALPHABET + jamo)
    aligner = LyricsAligner(emission_model=model)
    from karaoke_engine.align.lyrics import parse_lyrics

    [line] = parse_lyrics("한\n")
    tokens = aligner._tokens(line, [model.vocab], "ko")

    assert tokens.ids == tuple((model.vocab.ids[ch],) for ch in jamo)
    assert tokens.owner == (0, 0, 0)


def test_provenance_names_the_model_that_aligned_the_song(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from karaoke_engine.align import aligner as module

    monkeypatch.setattr(module, "_vocab_of", lambda name: _vocab(ALPHABET))
    aligner = LyricsAligner()

    names = aligner._names_for("hi", [])
    assert names == ("music-w2vbert-ctc",)  # nothing to read yet: the first choice
    assert "w2v-bert-2.0-music-lyrics-ctc@" in aligner.model_for_language("hi")
    assert aligner.fallback_for("hi") == "music-w2vbert-ctc"
    assert aligner.fallback_for("gl") is None


def test_the_default_second_model_joins_each_language_s_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from karaoke_engine.align import aligner as module

    monkeypatch.setattr(module, "DEFAULT_SECOND", "music-w2vbert-ctc")

    assert LyricsAligner().model_names("gl") == ("nos-xlsr-300m-gl", "music-w2vbert-ctc")
    # A language the music model already aligns alone uses it once.
    assert LyricsAligner().model_names("it") == ("music-w2vbert-ctc",)


def test_a_model_chosen_by_hand_works_alone_unless_a_second_is_asked_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from karaoke_engine.align import aligner as module

    monkeypatch.setattr(module, "DEFAULT_SECOND", "music-w2vbert-ctc")

    assert LyricsAligner(model="omni-ctc-300m").model_names("gl") == ("omni-ctc-300m",)
    assert LyricsAligner(model="omni-ctc-300m", second="nos-w2vbert-gl").model_names("gl") == (
        "omni-ctc-300m",
        "nos-w2vbert-gl",
    )


def test_the_second_model_can_be_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from karaoke_engine.align import aligner as module

    monkeypatch.setattr(module, "DEFAULT_SECOND", "music-w2vbert-ctc")

    assert LyricsAligner(second="").model_names("gl") == ("nos-xlsr-300m-gl",)
    assert LyricsAligner(second_weight=0.0).model_names("gl") == ("nos-xlsr-300m-gl",)


def test_preparing_stores_the_big_models_in_16_bits_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from karaoke_engine.align import aligner as module

    halved: list[str] = []
    monkeypatch.setattr(module, "half_copy", lambda spec: halved.append(spec.repo))

    LyricsAligner().prepare_for("gl")
    LyricsAligner(device="cpu").prepare_for("gl")  # 32 bits on the CPU: no copy
    LyricsAligner(second="").prepare_for("gl")  # the Galician model alone is small

    assert halved == ["mrfakename/w2v-bert-2.0-music-lyrics-ctc"]


def test_an_aligner_with_its_own_models_prepares_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    from karaoke_engine.align import aligner as module

    halved: list[str] = []
    monkeypatch.setattr(module, "half_copy", lambda spec: halved.append(spec.repo))

    LyricsAligner(emission_model=ScriptedModel([])).prepare_for("gl")

    assert halved == []


class DeafModel(ScriptedModel):
    """Hears no letter at all: blank everywhere."""

    def __init__(self) -> None:
        super().__init__([])


def test_the_language_s_model_decides_how_often_a_line_is_sung(tmp_path: Path) -> None:
    # The second model is there to hear what the first misses, and its probabilities are spread
    # over time: where it hears little, the mean dulls every letter and singing a couplet again
    # no longer pays its cost. How often a line is sung is the first model's call.
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    peaks = []
    for start in (20, 140):
        peaks += _spell("ola mar", start) + _spell("vai vento", start + 50)

    lines = LyricsAligner(
        emission_model=ScriptedModel(peaks),
        second_emission_model=DeafModel(),
        second_weight=0.9,
        repeat_penalty=20.0,
    ).align_text(vocals, "Ola mar\nVai vento\n", "gl")

    assert _texts(lines) == ["Ola mar", "Vai vento", "Ola mar", "Vai vento"]
    assert [line.start for line in lines] == pytest.approx([0.4, 1.4, 2.8, 3.8])


def test_the_language_s_model_reads_the_repeat_marks(tmp_path: Path) -> None:
    vocals = _vocals(tmp_path, [(0.0, 8.0)], seconds=8.0)
    peaks = []
    for start in (20, 140):
        peaks += _spell("ola mar", start) + _spell("vai vento", start + 50)
    peaks += _spell("adeus", 260)

    lines = LyricsAligner(
        emission_model=ScriptedModel(peaks),
        second_emission_model=DeafModel(),
        second_weight=0.9,
        repeat_penalty=math.inf,
    ).align_text(vocals, "Ola mar\nVai vento (x2)\nAdeus\n", "gl")

    assert _texts(lines) == ["Ola mar", "Vai vento", "Ola mar", "Vai vento", "Adeus"]


def test_a_line_the_first_model_skips_can_still_be_placed_by_both(tmp_path: Path) -> None:
    # The first model hears nothing of the second line; the second model hears it clearly.
    vocals = _vocals(tmp_path, [(0.0, 6.0)])
    first = ScriptedModel(_spell("ola mar", 20))
    second = ScriptedModel(_spell("ola mar", 20) + _spell("vai vento", 150))

    lines = LyricsAligner(emission_model=first, second_emission_model=second).align_text(
        vocals, "Ola mar\nVai vento\n", "gl"
    )

    assert _texts(lines) == ["Ola mar", "Vai vento"]
    assert lines[1].start == pytest.approx(150 * HOP)


def test_the_sung_order_follows_the_path_and_keeps_left_out_lines_in_place() -> None:
    from karaoke_engine.align.aligner import _sung_order
    from karaoke_engine.align.ctc import BestPath, SegmentPath

    # Lines 0..4: 0 and 1 are left out, 2-3 are sung twice, 4 once at the end.
    paths = [
        SegmentPath(None),
        SegmentPath(None),
        SegmentPath([(20, 21)], repeats=([(40, 41)],)),
        SegmentPath([(30, 31)], repeats=([(50, 51)],)),
        SegmentPath([(60, 61)]),
    ]
    order = [0, 1, 2, 3, 4]

    sung = _sung_order(order, BestPath(paths, 0.0))

    # 0 and 1 before everything; 2 3 2 3 as sung; 4 at the end.
    assert sung == [0, 1, 2, 3, 2, 3, 4]


def test_a_line_left_out_between_two_sung_ones_waits_after_the_first() -> None:
    from karaoke_engine.align.aligner import _sung_order
    from karaoke_engine.align.ctc import BestPath, SegmentPath

    paths = [
        SegmentPath([(5, 6)], repeats=([(40, 41)],)),
        SegmentPath(None),
        SegmentPath([(20, 21)]),
    ]

    assert _sung_order([0, 1, 2], BestPath(paths, 0.0)) == [0, 1, 2, 0]
