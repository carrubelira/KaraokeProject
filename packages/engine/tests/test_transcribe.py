import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.steps import Transcriber
from karaoke_engine.transcribe import MODELS, WhisperTranscriber

RATE = 16000


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str


@dataclass
class FakeInfo:
    language: str


class FakeWhisper:
    def __init__(self, segments: list[FakeSegment], language: str = "pt") -> None:
        self.segments = segments
        self.language = language
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio: np.ndarray, **options: object) -> tuple[object, FakeInfo]:
        self.calls.append({**options, "seconds": len(audio) / RATE})
        return iter(self.segments), FakeInfo(self.language)


def _vocals(tmp_path: Path, voiced: list[tuple[float, float]], seconds: float = 8.0) -> Path:
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


def _transcribe(tmp_path: Path, segments: list[FakeSegment], voiced: list[tuple[float, float]]):  # type: ignore[no-untyped-def]
    whisper = FakeWhisper(segments)
    transcriber = WhisperTranscriber(whisper=whisper)
    return transcriber.transcribe(_vocals(tmp_path, voiced), "gl"), whisper


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_keeps_the_requested_language(tmp_path: Path) -> None:
    transcript, whisper = _transcribe(tmp_path, [FakeSegment(0.5, 1.5, " Ola mar ")], [(0, 2)])

    assert transcript.language == "gl"
    assert [s.text for s in transcript.segments] == ["Ola mar"]
    assert whisper.calls[0]["language"] == "gl"
    assert whisper.calls[0]["condition_on_previous_text"] is False


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_drops_segments_without_voice(tmp_path: Path) -> None:
    segments = [FakeSegment(0.5, 1.5, "Ola mar"), FakeSegment(4.0, 6.0, "Grazas por ver o vídeo")]

    transcript, _ = _transcribe(tmp_path, segments, [(0, 2)])

    assert [s.text for s in transcript.segments] == ["Ola mar"]


@pytest.mark.usefixtures("ffmpeg")
def test_transcriber_drops_loops_where_the_voice_barely_sounds(tmp_path: Path) -> None:
    segments = [
        FakeSegment(0.0, 1.0, "vai o vento"),
        FakeSegment(1.0, 3.0, "la la la la la la la la la la la la"),
        *(FakeSegment(3.0 + i, 4.0 + i, "e ti que fas") for i in range(4)),
    ]

    # Voice under the first line, then only in short bursts.
    transcript, _ = _transcribe(tmp_path, segments, [(0, 1.5), (3.0, 3.5), (4.0, 4.5)])

    assert [s.text for s in transcript.segments] == ["vai o vento", "e ti que fas", "e ti que fas"]


@pytest.mark.usefixtures("ffmpeg")
def test_a_chorus_sung_again_and_again_is_kept(tmp_path: Path) -> None:
    segments = [FakeSegment(float(i), i + 1.0, "e ti que fas") for i in range(4)]

    transcript, _ = _transcribe(tmp_path, segments, [(0, 8)])

    assert [s.text for s in transcript.segments] == ["e ti que fas"] * 4


def test_transcriber_is_a_transcriber() -> None:
    assert isinstance(WhisperTranscriber(), Transcriber)


def test_models_are_pinned() -> None:
    assert {"large-v3-turbo", "nos-turbo-gl", "hitz-large-v3-gl", "bsc-los"} <= set(MODELS)
    assert all(len(spec.revision) == 40 for spec in MODELS.values())


def test_segmenter_cuts_on_punctuation_and_length() -> None:
    from karaoke_engine.steps import Transcript, TranscriptSegment
    from karaoke_engine.transcribe import LineSegmenter

    long = " ".join(f"p{i}" for i in range(12))
    transcript = Transcript(
        language="gl",
        segments=(
            TranscriptSegment(0.0, 3.0, "Ola, mar. Vai o vento!"),
            TranscriptSegment(3.0, 9.0, long),
        ),
    )

    lines = LineSegmenter().segment(transcript)

    assert lines == ["Ola, mar.", "Vai o vento!", " ".join(f"p{i}" for i in range(6)),
                     " ".join(f"p{i}" for i in range(6, 12))]  # fmt: skip


def test_galician_defaults_to_the_galician_model() -> None:
    assert WhisperTranscriber().model_for_language("gl").startswith("HiTZ/whisper-large-v3-gl@")
    assert (
        WhisperTranscriber()
        .model_for_language("es")
        .startswith("dropbox-dash/faster-whisper-large-v3-turbo@")
    )


def test_conversion_runs_in_its_own_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.transcribe as transcribe

    ran: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        ran.append(command)
        (Path(command[-1]) / "model.bin").parent.mkdir(parents=True, exist_ok=True)
        (Path(command[-1]) / "model.bin").write_bytes(b"x")

    monkeypatch.setattr(transcribe, "CACHE", tmp_path)
    monkeypatch.setattr(transcribe.subprocess, "run", fake_run)
    monkeypatch.setattr(transcribe, "_download", lambda spec: tmp_path / "hf")
    monkeypatch.setattr(transcribe, "_available_memory_gb", lambda: 7.5)

    target = transcribe.prepare("hitz-large-v3-gl")

    assert (target / "model.bin").is_file()
    assert ran[0][1:3] == ["-m", "karaoke_engine.transcribe"]
    assert transcribe.prepare("hitz-large-v3-gl") == target
    assert len(ran) == 1


def test_segmenter_drops_transcription_notes() -> None:
    from karaoke_engine.steps import Transcript, TranscriptSegment
    from karaoke_engine.transcribe import LineSegmenter

    transcript = Transcript(
        language="es",
        segments=(
            TranscriptSegment(0.0, 2.0, "[Música] ♪ (risas) Ola mar x2"),
            TranscriptSegment(2.0, 3.0, "♪♪"),
            TranscriptSegment(3.0, 4.0, "Estribillo: vai (o vento)"),
        ),
    )

    assert LineSegmenter().segment(transcript) == ["Ola mar", "Estribillo: vai o vento"]


def test_conversion_happens_aside_and_lands_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.transcribe as transcribe

    def failing_run(command: list[str], check: bool) -> None:
        Path(command[-1]).mkdir(parents=True)
        (Path(command[-1]) / "model.bin").write_bytes(b"half")
        raise subprocess.CalledProcessError(-9, command)

    monkeypatch.setattr(transcribe, "CACHE", tmp_path)
    monkeypatch.setattr(transcribe.subprocess, "run", failing_run)
    monkeypatch.setattr(transcribe, "_download", lambda spec: tmp_path / "hf")
    monkeypatch.setattr(transcribe, "_available_memory_gb", lambda: 7.5)

    with pytest.raises(transcribe.ModelError, match="convert"):
        transcribe.prepare("hitz-large-v3-gl")

    assert not list(tmp_path.glob("hitz-large-v3-gl-*/model.bin"))


def test_conversion_needs_free_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import karaoke_engine.transcribe as transcribe

    monkeypatch.setattr(transcribe, "CACHE", tmp_path)
    monkeypatch.setattr(transcribe, "_download", lambda spec: tmp_path / "hf")
    monkeypatch.setattr(transcribe, "_available_memory_gb", lambda: 4.0)

    with pytest.raises(transcribe.ModelError, match="GB"):
        transcribe.prepare("hitz-large-v3-gl")


@pytest.mark.usefixtures("ffmpeg")
def test_a_long_chant_where_the_voice_sounds_is_cut_to_one_line(tmp_path: Path) -> None:
    segments = [FakeSegment(0.0, 6.0, " ".join(["Abater!"] * 30))]

    transcript, _ = _transcribe(tmp_path, segments, [(0, 8)])

    assert [s.text for s in transcript.segments] == [" ".join(["Abater!"] * 8)]


@pytest.mark.usefixtures("ffmpeg")
def test_temperatures_reach_whisper(tmp_path: Path) -> None:
    whisper = FakeWhisper([FakeSegment(0.5, 1.5, "Ola")])

    WhisperTranscriber(whisper=whisper, temperatures=(0.0, 0.5)).transcribe(
        _vocals(tmp_path, [(0, 2)]), "gl"
    )

    assert whisper.calls[0]["temperature"] == [0.0, 0.5]


def test_segmenter_keeps_names_that_look_like_repeat_marks() -> None:
    from karaoke_engine.steps import Transcript, TranscriptSegment
    from karaoke_engine.transcribe import LineSegmenter

    transcript = Transcript(
        language="gl",
        segments=(TranscriptSegment(0.0, 2.0, "Baixo do BMW X6 x2"),),
    )

    assert LineSegmenter().segment(transcript) == ["Baixo do BMW X6"]


def test_a_transcriber_killed_for_memory_is_an_error_not_a_hang(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from karaoke_engine.transcribe import transcribe_in_child

    # The child process imports the stand-in by name, as it would the real worker.
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    import child_crash

    # A MemoryError: the server reports it as "out of memory" and tries once more.
    with pytest.raises(MemoryError, match="out of memory"):
        transcribe_in_child(tmp_path / "vocals.wav", "gl", work=child_crash.die)


@pytest.mark.usefixtures("ffmpeg")
def test_each_stretch_of_singing_is_transcribed_on_its_own(tmp_path: Path) -> None:
    whisper = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])
    vocals = _vocals(tmp_path, [(0, 2), (10, 12)], seconds=14.0)

    transcript = WhisperTranscriber(whisper=whisper, by_voice=True).transcribe(vocals, "gl")

    # Two stretches with their margin of a quarter of a second, not the 14 s of the song.
    assert [call["seconds"] for call in whisper.calls] == pytest.approx([2.25, 2.5], abs=0.05)
    # The voice is already found: Whisper's own speech detector would drop sung passages.
    assert all(call["vad_filter"] is False for call in whisper.calls)
    assert [(s.start, s.text) for s in transcript.segments] == [
        (pytest.approx(0.3, abs=0.03), "Ola mar"),
        (pytest.approx(10.05, abs=0.03), "Ola mar"),
    ]


@pytest.mark.usefixtures("ffmpeg")
def test_a_segment_never_runs_past_its_stretch(tmp_path: Path) -> None:
    whisper = FakeWhisper([FakeSegment(0.3, 29.0, "Ola mar")])
    vocals = _vocals(tmp_path, [(0, 2)], seconds=14.0)

    transcript = WhisperTranscriber(whisper=whisper, by_voice=True).transcribe(vocals, "gl")

    [segment] = transcript.segments
    assert segment.end == pytest.approx(2.25, abs=0.05)


@pytest.mark.usefixtures("ffmpeg")
def test_without_stretches_the_whole_song_goes_to_whisper_at_once(tmp_path: Path) -> None:
    whisper = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])
    vocals = _vocals(tmp_path, [(0, 2), (10, 12)], seconds=14.0)

    WhisperTranscriber(whisper=whisper, by_voice=False).transcribe(vocals, "gl")

    assert [call["seconds"] for call in whisper.calls] == pytest.approx([14.0])
    assert whisper.calls[0]["vad_filter"] is True


@pytest.mark.usefixtures("ffmpeg")
def test_stretches_can_be_made_shorter(tmp_path: Path) -> None:
    # Two phrases of 8 s, a second apart: one stretch of 17 s, or two when 10 s is the most.
    vocals = _vocals(tmp_path, [(0, 8), (9, 17)], seconds=18.0)
    long = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])
    short = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])

    WhisperTranscriber(whisper=long, by_voice=True).transcribe(vocals, "gl")
    WhisperTranscriber(whisper=short, by_voice=True, stretch_seconds=10.0).transcribe(vocals, "gl")

    assert len(long.calls) == 1
    assert len(short.calls) == 2


@pytest.mark.usefixtures("ffmpeg")
def test_each_model_reads_stretches_of_its_own_length(tmp_path: Path) -> None:
    # Two phrases of 8 s a second apart. A turbo model loses the thread in long stretches and
    # reads them one by one; a large one uses the context and reads both together.
    vocals = _vocals(tmp_path, [(0, 8), (9, 17)], seconds=18.0)
    turbo = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])
    large = FakeWhisper([FakeSegment(0.3, 1.5, "Ola mar")])

    WhisperTranscriber(model="large-v3-turbo", whisper=turbo, by_voice=True).transcribe(
        vocals, "en"
    )
    WhisperTranscriber(model="hitz-large-v3-gl", whisper=large, by_voice=True).transcribe(
        vocals, "gl"
    )

    assert len(turbo.calls) == 2
    assert len(large.calls) == 1


def test_every_model_says_how_long_a_stretch_it_reads() -> None:
    assert MODELS["large-v3-turbo"].stretch == MODELS["nos-turbo-gl"].stretch == 12.0
    assert MODELS["hitz-large-v3-gl"].stretch == 28.0
    assert all(0 < spec.stretch <= 28.0 for spec in MODELS.values())
