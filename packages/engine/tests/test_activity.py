import numpy as np

from karaoke_engine.align.activity import vocal_activity, voiced_stretches

RATE = 16000
HOP = 0.02


def _tone(seconds: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * RATE)) / RATE
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(round(seconds * RATE), dtype=np.float32)


def test_activity_follows_tone_bursts() -> None:
    samples = np.concatenate([_silence(1), _tone(1), _silence(2), _tone(1), _silence(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert len(active) == round(6 / HOP)
    expected = np.zeros(len(active), dtype=bool)
    expected[50:100] = True
    expected[200:250] = True
    assert np.count_nonzero(active != expected) <= 4


def test_quiet_bleed_is_not_voice() -> None:
    bleed = _tone(2, amplitude=0.5 * 10 ** (-45 / 20))
    samples = np.concatenate([_tone(1), bleed, _tone(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert not active[60:140].any()


def test_short_gap_is_filled() -> None:
    samples = np.concatenate([_tone(1), _silence(0.1), _tone(1)])

    active = vocal_activity(samples, RATE, HOP)

    assert active[45:60].all()


def test_short_blip_is_dropped() -> None:
    samples = np.concatenate([_silence(1), _tone(0.06), _silence(1)])

    assert not vocal_activity(samples, RATE, HOP).any()


def test_silent_input_has_no_voice() -> None:
    assert not vocal_activity(_silence(2), RATE, HOP).any()


def _flags(*runs: tuple[float, float], seconds: float) -> np.ndarray:
    active = np.zeros(round(seconds / HOP), dtype=bool)
    for start, end in runs:
        active[round(start / HOP) : round(end / HOP)] = True
    return active


def test_phrases_close_together_share_a_stretch() -> None:
    active = _flags((1, 3), (3.4, 6), (20, 24), seconds=30)

    stretches = voiced_stretches(active, HOP, pad=0.0)

    assert stretches == [(1.0, 6.0), (20.0, 24.0)]


def test_stretches_grow_up_to_the_limit_and_cut_in_the_silences() -> None:
    # Six phrases of 8 s with 2 s between them: three fit in 30 s (8 + 2 + 8 + 2 + 8 = 28).
    runs = [(10.0 * k, 10.0 * k + 8) for k in range(6)]
    active = _flags(*runs, seconds=60)

    stretches = voiced_stretches(active, HOP, limit=30.0, pad=0.0)

    assert stretches == [(0.0, 28.0), (30.0, 58.0)]


def test_a_long_break_always_cuts() -> None:
    active = _flags((0, 5), (14, 19), seconds=20)

    assert voiced_stretches(active, HOP, limit=30.0, max_gap=7.0, pad=0.0) == [
        (0.0, 5.0),
        (14.0, 19.0),
    ]


def test_a_phrase_longer_than_the_limit_is_cut_at_its_longest_pause() -> None:
    # 40 s of rap with two short breaths: at 12.0-12.2 s and at 22.0-22.4 s (the longer one).
    active = _flags((0, 12), (12.2, 22), (22.4, 40), seconds=40)

    stretches = voiced_stretches(active, HOP, limit=30.0, pad=0.0)

    assert stretches == [(0.0, 22.0), (22.4, 40.0)]


def test_voice_without_a_single_pause_is_cut_evenly() -> None:
    active = _flags((0, 70), seconds=70)

    stretches = voiced_stretches(active, HOP, limit=30.0, pad=0.0)

    assert [round(end - start, 1) for start, end in stretches] == [23.3, 23.3, 23.3]
    assert stretches[0][0] == 0.0
    assert stretches[-1][1] == 70.0


def test_padding_never_reaches_past_half_the_silence_or_the_ends() -> None:
    active = _flags((0.1, 3), (3.8, 6), (9.9, 10), seconds=10)

    stretches = voiced_stretches(active, HOP, min_gap=0.5, max_gap=0.6, pad=0.5)

    # 0.8 s between the first two (0.4 s each at most), 3.9 s before the last one.
    assert stretches == [(0.0, 3.4), (3.4, 6.5), (9.4, 10.0)]


def test_no_voice_no_stretches() -> None:
    assert voiced_stretches(np.zeros(100, dtype=bool), HOP) == []
