from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from karaoke_engine.captions import speech
from karaoke_engine.captions.rules import TimedWord
from karaoke_engine.captions.speech import SpeechTranscript
from karaoke_engine.cli import main


def fake_transcribe(audio: Path, language: str, **options: Any) -> SpeechTranscript:
    words = tuple(
        TimedWord(w, 0.5 + i * 0.4, 0.8 + i * 0.4, 0.9) for i, w in enumerate(["Era", "o", "mar."])
    )
    return SpeechTranscript(words, ((0.4, 2.0),), (), "fake@0")


@pytest.fixture
def fake_model(monkeypatch: pytest.MonkeyPatch) -> None:
    from karaoke_engine.captions import pipeline

    monkeypatch.setattr(speech, "transcribe_speech_in_child", fake_transcribe)
    monkeypatch.setattr(pipeline, "default_steps", lambda: ())


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def test_captions_needs_something_to_caption(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["captions"]) == 2
    assert "video" in capsys.readouterr().err


@pytest.mark.usefixtures("fake_model", "cache")
def test_captions_reports_each_video_and_fails_if_one_fails(
    tmp_path: Path, make_video: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    video = make_video(tmp_path / "MVI_0704.MP4")
    broken = tmp_path / "roto.mp4"
    broken.write_bytes(b"not a video")
    assert main(["captions", str(tmp_path), "--no-shots"]) == 1
    out = capsys.readouterr()
    assert "MVI_0704.MP4: 1 subtitle" in out.out
    assert "roto.mp4: error" in out.out
    assert "[1/2]" in out.err
    assert (tmp_path / "MVI_0704.gl.srt").is_file()
    assert video.is_file()


@pytest.mark.usefixtures("fake_model", "cache")
def test_captions_skips_a_video_that_has_them(
    tmp_path: Path, make_video: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    make_video(tmp_path / "a.mp4")
    assert main(["captions", str(tmp_path / "a.mp4"), "--no-shots"]) == 0
    assert main(["captions", str(tmp_path / "a.mp4"), "--no-shots"]) == 0
    assert "--force" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_model", "cache")
def test_captions_from_srt_rebuilds_the_vtt(
    tmp_path: Path, make_video: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    make_video(tmp_path / "a.mp4")
    assert main(["captions", str(tmp_path / "a.mp4"), "--no-shots"]) == 0
    srt = tmp_path / "a.gl.srt"
    srt.write_text(srt.read_text(encoding="utf-8-sig").replace("mar", "mar de Lira"), "utf-8-sig")
    assert main(["captions", "--from-srt", str(srt)]) == 0
    assert "mar de Lira" in (tmp_path / "a.gl.vtt").read_text(encoding="utf-8")


def test_audio_track_counts_from_one(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["captions", str(tmp_path), "--audio-track", "0"]) == 2
    assert "from 1" in capsys.readouterr().err


def test_a_folder_without_videos_says_so(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "notas.txt").write_text("nada")
    assert main(["captions", str(tmp_path)]) == 1
    assert "no videos" in capsys.readouterr().err


@pytest.mark.usefixtures("fake_model", "cache")
def test_captions_say_how_long_the_long_steps_should_take(
    tmp_path: Path, make_video: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    make_video(tmp_path / "a.mp4")
    assert main(["captions", str(tmp_path / "a.mp4"), "--no-shots"]) == 0
    err = capsys.readouterr().err
    assert "transcribing (under a minute)" in err


def test_estimates_scale_with_the_length_of_the_video() -> None:
    from karaoke_engine.captions.pipeline import estimate

    assert estimate("transcribe", 3600.0) == pytest.approx(330.0)
    assert estimate("speakers", 1800.0) == pytest.approx(45.0)
    assert estimate("write", 3600.0) is None
