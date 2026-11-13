import itertools

import numpy as np
import pytest

from karaoke_bench.captions import (
    Clip,
    RefUtterance,
    caption_metrics,
    plan_dialogues,
    speech_bounds,
    violations,
)
from karaoke_engine.captions.rules import Caption, Rules, TimedWord


def clips() -> list[Clip]:
    out = []
    for gender in ("female", "male"):
        for s in range(6):
            speaker = f"g{gender[0]}_{s:05d}"
            out += [
                Clip(speaker, gender, f"{speaker}_{i:011d}", f"Frase {i} de {speaker}.", 4.0)
                for i in range(30)
            ]
    return out


def test_dialogue_plans_are_deterministic() -> None:
    assert plan_dialogues(clips(), count=4, seconds=60, seed=3) == plan_dialogues(
        clips(), count=4, seconds=60, seed=3
    )
    assert plan_dialogues(clips(), count=4, seconds=60, seed=3) != plan_dialogues(
        clips(), count=4, seconds=60, seed=4
    )


def test_dialogues_alternate_two_speakers_in_interview_turns() -> None:
    for plan in plan_dialogues(clips(), count=4, seconds=60, seed=0):
        roles = [part.role for part in plan.parts]
        turns = [(role, len(list(group))) for role, group in _groups(roles)]
        assert turns[0][0] == "B"
        assert all(a[0] != b[0] for a, b in itertools.pairwise(turns))
        assert all(1 <= n <= 2 for role, n in turns if role == "B")
        assert all(3 <= n <= 8 for role, n in turns if role == "A")
        speakers = {part.role: part.clip.speaker for part in plan.parts}
        assert len({p.clip.speaker for p in plan.parts}) == 2
        assert speakers["A"] != speakers["B"]
        assert sum(p.clip.seconds + p.pause for p in plan.parts) >= 60
        assert all(0.1 <= p.pause <= 1.5 for p in plan.parts[1:])


def test_half_the_dialogues_pair_speakers_of_the_same_gender() -> None:
    plans = plan_dialogues(clips(), count=4, seconds=60, seed=0)
    same = [len({p.clip.gender for p in plan.parts}) == 1 for plan in plans]
    assert same == [True, False, True, False]


def test_speech_bounds_trim_silence() -> None:
    rate = 16000
    samples = np.zeros(3 * rate, dtype=np.float32)
    t = np.arange(rate) / rate
    samples[rate : 2 * rate] = 0.3 * np.sin(2 * np.pi * 200 * t)
    start, end = speech_bounds(samples, rate)
    assert start == pytest.approx(1.0, abs=0.03)
    assert end == pytest.approx(2.0, abs=0.03)


REFERENCE = [
    RefUtterance(0.5, 1.7, "Ola, bo día.", "B"),
    RefUtterance(2.5, 4.5, "Nacín aquí mesmo.", "A"),
]


def _words(speakers: dict[str, str]) -> list[TimedWord]:
    out = []
    for utterance in REFERENCE:
        tokens = utterance.text.split()
        step = (utterance.end - utterance.start) / len(tokens)
        out += [
            TimedWord(w, utterance.start + i * step, utterance.start + (i + 1) * step, 0.9,
                      speakers[utterance.speaker])
            for i, w in enumerate(tokens)
        ]  # fmt: skip
    return out


def _captions(words: list[TimedWord]) -> list[Caption]:
    return [
        Caption(
            u.start,
            u.end,
            (u.text,),
            (None,),
            tuple(w for w in words if u.start <= w.start < u.end),
        )
        for u in REFERENCE
    ]


def test_metrics_on_a_perfect_hypothesis_are_zero() -> None:
    words = _words({"A": "A", "B": "B"})
    metrics = caption_metrics(REFERENCE, _captions(words), words, Rules(), 25.0)
    assert metrics.wer == 0.0
    assert metrics.speaker_word_error == 0.0
    assert metrics.onset_error_median == 0.0
    assert metrics.onset_error_p90 == 0.0
    assert metrics.onset_missing == 0
    assert sum(metrics.violations.values()) == 0


def test_speaker_error_is_label_permutation_invariant() -> None:
    words = _words({"A": "B", "B": "A"})
    metrics = caption_metrics(REFERENCE, _captions(words), words, Rules(), 25.0)
    assert metrics.speaker_word_error == 0.0


def test_speaker_error_is_none_without_speakers() -> None:
    words = [TimedWord(w.text, w.start, w.end, w.confidence) for w in _words({"A": "A", "B": "B"})]
    metrics = caption_metrics(REFERENCE, _captions(words), words, Rules(), 25.0)
    assert metrics.speaker_word_error is None


def test_onset_error_measures_late_captions() -> None:
    words = _words({"A": "A", "B": "B"})
    late = [Caption(c.start + 0.2, c.end, c.lines, c.speakers, c.words) for c in _captions(words)]
    metrics = caption_metrics(REFERENCE, late, words, Rules(), 25.0)
    assert metrics.onset_error_median == pytest.approx(0.2)


def test_violations_count_each_rule() -> None:
    captions = [
        Caption(0.0, 1.0, ("x" * 43,), (None,)),
        Caption(1.02, 2.0, ("Un", "dous", "tres"), (None, None, None)),
        Caption(1.9, 2.3, ("Catro",), (None,)),
        Caption(3.0, 11.0, ("Cinco",), (None,)),
        Caption(11.1, 12.0, ("Daquela era todo casas baixas e o porto",), (None,)),
    ]
    assert violations(captions, Rules(), 25.0) == {
        "lines": 1, "chars": 1, "cps": 2, "short": 1, "long": 1, "overlap": 1, "gap": 1,
    }  # fmt: skip


def _groups(items: list[str]):  # type: ignore[no-untyped-def]
    import itertools

    return itertools.groupby(items)


def test_run_writes_a_report(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import json
    import wave

    from karaoke_bench.captions import run_captions
    from karaoke_bench.paths import BenchPaths
    from karaoke_engine.captions.speech import SpeechTranscript

    paths = BenchPaths(tmp_path / "bench")
    folder = paths.data / "speech-gl" / "dialogues"
    folder.mkdir(parents=True)
    with wave.open(str(folder / "dialogue-01.wav"), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\0\0" * 16000 * 6)
    (folder / "dialogue-01.json").write_text(
        json.dumps(
            [
                {"start": u.start, "end": u.end, "text": u.text, "speaker": u.speaker}
                for u in REFERENCE
            ]
        )
    )
    pipeline = tmp_path / "captions-fake.toml"
    pipeline.write_text('[captions]\nmodel = "fake"\nbeam_size = 1\n')

    def transcribe(audio, language, **options):  # type: ignore[no-untyped-def]
        assert options == {"model": "fake", "beam_size": 1}
        return SpeechTranscript(tuple(_words({"A": "A", "B": "B"})), (), (), "fake@0")

    report = run_captions(paths, pipeline, transcribe=transcribe)
    results = json.loads((report / "results.json").read_text())
    assert results["pipeline"] == "captions-fake"
    assert results["total"]["wer"] == 0.0
    assert results["dialogues"][0]["name"] == "dialogue-01"
    assert (report / "summary.md").is_file()


def test_cli_captions_without_dialogues_says_how_to_make_them(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    from karaoke_bench.cli import main

    pipeline = tmp_path / "captions-x.toml"
    pipeline.write_text("[captions]\n")
    assert main(["--bench-dir", str(tmp_path), "captions", "--pipeline", str(pipeline)]) == 1
    assert "fetch-speech" in capsys.readouterr().err
