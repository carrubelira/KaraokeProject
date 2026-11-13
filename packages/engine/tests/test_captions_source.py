import hashlib
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from karaoke_engine.align.audio import load_mono16k
from karaoke_engine.captions.source import cache_key, probe_source, read_source


@pytest.fixture(scope="module")
def video(tmp_path_factory: pytest.TempPathFactory, make_video: Callable[..., Path]) -> Path:
    return make_video(tmp_path_factory.mktemp("cam") / "MVI_0001.MP4")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dominant_hz(samples: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(samples[16000:32000]))
    return float(np.argmax(spectrum) * 16000 / 16000)


@pytest.mark.usefixtures("ffmpeg")
def test_probe_reads_fps_duration_and_audio(video: Path) -> None:
    info = probe_source(video)
    assert info.fps == pytest.approx(25.0)
    assert info.duration == pytest.approx(8.0, abs=0.1)
    assert (info.width, info.height) == (160, 120)
    assert info.audio_streams == 1
    assert info.audio_index == 0
    assert info.size == video.stat().st_size
    assert info.mtime_ns == video.stat().st_mtime_ns


@pytest.mark.usefixtures("ffmpeg")
def test_read_writes_16k_mono_flac_and_finds_the_cut(video: Path, tmp_path: Path) -> None:
    audio = tmp_path / "audio.flac"
    shots = read_source(probe_source(video), audio, shots=True)
    assert shots == [pytest.approx(4.0, abs=0.04)]
    samples = load_mono16k(audio)
    assert len(samples) == pytest.approx(8 * 16000, rel=0.02)
    assert _dominant_hz(samples) == pytest.approx(440, abs=2)
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.usefixtures("ffmpeg")
def test_read_without_shots_finds_none(video: Path, tmp_path: Path) -> None:
    assert read_source(probe_source(video), tmp_path / "audio.flac", shots=False) == []
    assert (tmp_path / "audio.flac").is_file()


@pytest.mark.usefixtures("ffmpeg")
def test_progress_is_reported(video: Path, tmp_path: Path) -> None:
    seen: list[float] = []
    read_source(probe_source(video), tmp_path / "a.flac", shots=False, on_progress=seen.append)
    assert seen
    assert seen == sorted(seen)
    assert 0.0 <= seen[-1] <= 1.0


@pytest.mark.usefixtures("ffmpeg")
def test_the_video_is_never_modified(video: Path, tmp_path: Path) -> None:
    before = (_sha256(video), video.stat().st_size, video.stat().st_mtime_ns)
    folder_before = sorted(video.parent.iterdir())
    read_source(probe_source(video), tmp_path / "audio.flac", shots=True)
    assert (_sha256(video), video.stat().st_size, video.stat().st_mtime_ns) == before
    assert sorted(video.parent.iterdir()) == folder_before


@pytest.mark.usefixtures("ffmpeg")
def test_second_audio_track_is_used_when_asked(
    tmp_path: Path, make_video: Callable[..., Path]
) -> None:
    video = make_video(tmp_path / "two.mov", tones=(440, 880))
    info = probe_source(video, audio_track=1)
    assert (info.audio_streams, info.audio_index) == (2, 1)
    read_source(info, tmp_path / "audio.flac", shots=False)
    assert _dominant_hz(load_mono16k(tmp_path / "audio.flac")) == pytest.approx(880, abs=2)


@pytest.mark.usefixtures("ffmpeg")
def test_an_audio_track_that_does_not_exist_is_a_clear_error(video: Path) -> None:
    with pytest.raises(ValueError, match="audio track 3"):
        probe_source(video, audio_track=3)


@pytest.mark.usefixtures("ffmpeg")
def test_no_audio_is_a_clear_error(tmp_path: Path, make_video: Callable[..., Path]) -> None:
    silent = make_video(tmp_path / "silent.mp4", audio=False)
    with pytest.raises(ValueError, match="no audio"):
        probe_source(silent)


@pytest.mark.usefixtures("ffmpeg")
def test_cache_key_changes_with_the_file_and_the_parts(video: Path, tmp_path: Path) -> None:
    info = probe_source(video)
    assert cache_key(info, "audio-1") == cache_key(info, "audio-1")
    assert cache_key(info, "audio-1") != cache_key(info, "audio-2")
    copy = tmp_path / "MVI_0001.MP4"
    copy.write_bytes(video.read_bytes())
    assert cache_key(probe_source(copy), "audio-1") != cache_key(info, "audio-1")
