import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

DEMO_JSON = Path(__file__).resolve().parents[3] / "fixtures/packages/demo-sintetico/karaoke.json"


@pytest.fixture
def bare_package(tmp_path: Path) -> Path:
    """A copy of the demo package with its karaoke.json only (no media yet)."""
    package = tmp_path / "demo"
    package.mkdir()
    shutil.copy(DEMO_JSON, package / "karaoke.json")
    return package


def _camera_video(out: Path, *, tones: tuple[int, ...] = (440,), audio: bool = True) -> Path:
    """8 s at 25 fps: 4 s of black, then 4 s of white (a cut at 4 s), an audio track per tone."""
    inputs = [
        "-f", "lavfi", "-i", "color=black:s=160x120:r=25:d=4",
        "-f", "lavfi", "-i", "color=white:s=160x120:r=25:d=4",
    ]  # fmt: skip
    maps = ["-map", "[v]"]
    for i, tone in enumerate(tones if audio else ()):
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={tone}:duration=8:sample_rate=48000"]
        maps += ["-map", f"{i + 2}:a"]
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", *inputs,
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", *maps,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)],
        check=True,
    )  # fmt: skip
    return out


@pytest.fixture(scope="session")
def make_video() -> Callable[..., Path]:
    """Makes a small camera-like video with a cut; skips without ffmpeg (like `ffmpeg`)."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are not installed")
    return _camera_video
