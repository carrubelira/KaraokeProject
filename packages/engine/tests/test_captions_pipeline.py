import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from karaoke_engine.captions import pipeline
from karaoke_engine.captions.formats import SRT_ENCODING, read_srt, to_srt
from karaoke_engine.captions.pipeline import (
    CaptionOptions,
    caption_all,
    caption_video,
    find_videos,
    rebuild_from_srt,
)
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import SpeechTranscript

SENTENCE = "Nacín aquí mesmo, na rúa de arriba. Daquela isto era todo casas baixas."


class FakeTranscriber:
    """Says SENTENCE from 0.5 s on, a word every 0.4 s, and counts its calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, audio: Path, language: str, **options: Any) -> SpeechTranscript:
        self.calls += 1
        assert audio.is_file()
        words = tuple(
            TimedWord(w, 0.5 + i * 0.4, 0.5 + i * 0.4 + 0.3, 0.9)
            for i, w in enumerate(SENTENCE.split())
        )
        return SpeechTranscript(words, ((0.4, 6.0),), (), "fake@0")


@pytest.fixture
def options(tmp_path: Path) -> CaptionOptions:
    return CaptionOptions(cache=tmp_path / "cache", transcribe=FakeTranscriber())


@pytest.fixture
def video(tmp_path: Path, make_video: Callable[..., Path]) -> Path:
    folder = tmp_path / "entrevista Xan á beira"
    folder.mkdir()
    return make_video(folder / "MVI_0704.MP4")


def _state(path: Path) -> tuple[str, int, int]:
    return (
        hashlib.sha256(path.read_bytes()).hexdigest(),
        path.stat().st_size,
        path.stat().st_mtime_ns,
    )


def test_writes_srt_vtt_and_review_next_to_the_video_and_nothing_else(
    video: Path, options: CaptionOptions
) -> None:
    result = caption_video(video, options)
    names = sorted(p.name for p in video.parent.iterdir())
    assert names == [
        "MVI_0704.MP4", "MVI_0704.gl.revisar.txt", "MVI_0704.gl.srt", "MVI_0704.gl.vtt"
    ]  # fmt: skip
    srt = (video.parent / "MVI_0704.gl.srt").read_bytes()
    assert srt.startswith(b"\xef\xbb\xbf1\r\n")
    captions = read_srt(srt.decode(SRT_ENCODING))
    assert " ".join(" ".join(c.lines) for c in captions) == SENTENCE
    assert (video.parent / "MVI_0704.gl.vtt").read_text(encoding="utf-8").startswith("WEBVTT")
    assert result.captions == len(captions)
    assert result.error is None
    assert result.skipped is None


def test_the_video_is_never_modified(video: Path, options: CaptionOptions) -> None:
    before = _state(video)
    caption_video(video, options)
    caption_video(
        video, CaptionOptions(cache=options.cache, transcribe=options.transcribe, force=True)
    )
    assert _state(video) == before


def test_existing_srt_is_skipped_without_force_and_backed_up_with_force(
    video: Path, options: CaptionOptions
) -> None:
    srt = video.parent / "MVI_0704.gl.srt"
    srt.write_text("1\r\n00:00:01,000 --> 00:00:02,000\r\nRevisado\r\n", encoding=SRT_ENCODING)
    result = caption_video(video, options)
    assert result.skipped is not None
    assert "Revisado" in srt.read_text(encoding=SRT_ENCODING)

    forced = CaptionOptions(cache=options.cache, transcribe=options.transcribe, force=True)
    caption_video(video, forced)
    assert "Revisado" not in srt.read_text(encoding=SRT_ENCODING)
    assert "Revisado" in (video.parent / "MVI_0704.gl.srt.bak").read_text(encoding=SRT_ENCODING)


def test_resumes_from_cache_without_transcribing_again(
    video: Path, options: CaptionOptions
) -> None:
    caption_video(video, options)
    forced = CaptionOptions(cache=options.cache, transcribe=options.transcribe, force=True)
    caption_video(video, forced)
    assert isinstance(options.transcribe, FakeTranscriber)
    assert options.transcribe.calls == 1


def test_find_videos_matches_extensions_in_any_case(tmp_path: Path) -> None:
    for name in ("b.MP4", "a.mov", "c.Mxf", "notas.txt", ".oculto.mp4", "d.mp4.part", "e.gl.srt"):
        (tmp_path / name).write_bytes(b"")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.mp4").write_bytes(b"")
    assert [p.name for p in find_videos([tmp_path])] == ["a.mov", "b.MP4", "c.Mxf"]
    assert find_videos([tmp_path / "b.MP4"]) == [tmp_path / "b.MP4"]


def test_paths_with_spaces_and_accents(video: Path, options: CaptionOptions) -> None:
    assert " " in str(video.parent)
    assert "á" in str(video.parent)
    assert caption_video(video, options).error is None
    assert (video.parent / "MVI_0704.gl.srt").is_file()


def test_failure_in_one_video_does_not_stop_the_batch(
    video: Path, options: CaptionOptions, tmp_path: Path
) -> None:
    broken = tmp_path / "roto.mp4"
    broken.write_bytes(b"not a video")
    results = caption_all([broken, video], options)
    assert [r.video for r in results] == [broken, video]
    assert results[0].error is not None
    assert results[1].error is None
    assert (video.parent / "MVI_0704.gl.srt").is_file()


def test_interrupted_write_leaves_no_partial_files(
    video: Path, options: CaptionOptions, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = pipeline._write_part

    def failing(path: Path, text: str, encoding: str) -> None:
        if path.name.endswith(".vtt.part"):
            raise OSError("disk unplugged")
        real(path, text, encoding)

    monkeypatch.setattr(pipeline, "_write_part", failing)
    result = caption_all([video], options)[0]
    assert result.error is not None
    assert "disk unplugged" in result.error
    assert sorted(p.name for p in video.parent.iterdir()) == ["MVI_0704.MP4"]


def test_from_srt_rebuilds_vtt_with_the_edited_text(video: Path, options: CaptionOptions) -> None:
    caption_video(video, options)
    srt = video.parent / "MVI_0704.gl.srt"
    srt.write_text(
        srt.read_text(encoding=SRT_ENCODING).replace("Nacín", "Nacín eu"), encoding=SRT_ENCODING
    )
    result = rebuild_from_srt(srt, options)
    assert result.error is None
    vtt = (video.parent / "MVI_0704.gl.vtt").read_text(encoding="utf-8")
    assert "Nacín eu" in vtt
    assert "revisad" in vtt.split("\n\n")[1].lower()


def test_from_srt_refuses_a_constant_offset(video: Path, options: CaptionOptions) -> None:
    caption_video(video, options)
    srt = video.parent / "MVI_0704.gl.srt"
    vtt = video.parent / "MVI_0704.gl.vtt"
    before = vtt.read_bytes()
    captions = read_srt(srt.read_text(encoding=SRT_ENCODING))
    shifted = [c.__class__(c.start + 3600, c.end + 3600, c.lines, c.speakers) for c in captions]
    srt.write_text(to_srt(shifted), encoding=SRT_ENCODING)
    result = rebuild_from_srt(srt, options)
    assert result.error is not None
    assert "3600" in result.error
    assert vtt.read_bytes() == before


def test_caption_audio_captions_a_sound_file_for_the_bench(
    tmp_path: Path, options: CaptionOptions
) -> None:
    import wave

    audio = tmp_path / "dialogue.wav"
    with wave.open(str(audio), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\0\0" * 16000 * 8)
    captions, transcript = pipeline.caption_audio(audio, "gl", options, fps=25.0)
    assert " ".join(" ".join(c.lines) for c in captions) == SENTENCE
    assert transcript.model == "fake@0"
    assert (
        sorted(p.name for p in tmp_path.iterdir()) == ["cache", "dialogue.wav"]
        or not (tmp_path / "cache").exists()
    )


def test_cuts_are_found_while_transcribing(
    video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    transcribing = threading.Event()
    seen_during: list[bool] = []

    def find_shots(info: Any, work: Path, *, on_progress: Any = None) -> list[float]:
        seen_during.append(transcribing.wait(timeout=5))
        return [4.0]

    class Waiting(FakeTranscriber):
        def __call__(self, audio: Path, language: str, **options: Any) -> SpeechTranscript:
            transcribing.set()
            return super().__call__(audio, language, **options)

    monkeypatch.setattr(pipeline, "find_shots", find_shots)
    result = caption_video(video, CaptionOptions(cache=tmp_path / "c", transcribe=Waiting()))
    assert result.error is None
    assert seen_during == [True]


def test_without_shots_no_cuts_are_looked_for(
    video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: Any, **kwargs: Any) -> list[float]:
        raise AssertionError("looked for cuts")

    monkeypatch.setattr(pipeline, "find_shots", fail)
    options = CaptionOptions(cache=tmp_path / "c", transcribe=FakeTranscriber(), shots=False)
    assert caption_video(video, options).error is None
