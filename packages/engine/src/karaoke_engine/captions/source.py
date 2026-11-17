"""The interview video, read once and only read.

Reading only the audio of a 4K interview goes at about 30 times real time (an hour in two
minutes from a USB disk); decoding its picture to find the cuts between shots goes at about 6
times, so the cuts are found by a second ffmpeg while Whisper transcribes (the decoder and the
model use different parts of the graphics card). The video file is only ever opened for reading;
everything ffmpeg writes goes to the cache, under a side name that takes its final one when the
pass has finished.
"""

import hashlib
import json
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_FFMPEG = ("ffmpeg", "-nostdin", "-v", "error", "-y", "-progress", "pipe:1", "-nostats")
# scdet's score, from 0 to 100 (its default): a cut, not a camera move or a change of light.
_SCENE_THRESHOLD = 10
_SHOT_WIDTH = 320
_PTS_TIME = re.compile(r"pts_time:([0-9.]+)")


@dataclass(frozen=True)
class SourceInfo:
    path: Path
    duration: float
    fps: float
    audio_streams: int
    audio_index: int  # among the audio streams, from 0
    width: int
    height: int
    size: int
    mtime_ns: int


def probe_source(path: Path, audio_track: int | None = None) -> SourceInfo:
    """What the video holds; `audio_track` picks an audio stream (from 0), else the default."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise ValueError(f"{path.name}: ffprobe cannot read it ({result.stderr.strip()[-200:]})")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    videos = [
        s for s in streams
        if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")
    ]  # fmt: skip
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos:
        raise ValueError(f"{path.name} has no video stream")
    if not audios:
        raise ValueError(f"{path.name} has no audio track to transcribe")
    if audio_track is None:
        defaults = [i for i, s in enumerate(audios) if s.get("disposition", {}).get("default")]
        audio_index = defaults[0] if defaults else 0
    elif 0 <= audio_track < len(audios):
        audio_index = audio_track
    else:
        raise ValueError(f"{path.name} has no audio track {audio_track} ({len(audios)} tracks)")
    video = videos[0]
    stat = path.stat()
    return SourceInfo(
        path=path,
        duration=float(data.get("format", {}).get("duration") or video.get("duration") or 0.0),
        fps=_rate(video.get("avg_frame_rate")) or _rate(video.get("r_frame_rate")) or 25.0,
        audio_streams=len(audios),
        audio_index=audio_index,
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
    )


def read_source(
    info: SourceInfo, audio_out: Path, *, on_progress: Callable[[float], None] | None = None
) -> None:
    """Writes the speech track to `audio_out` (16 kHz mono FLAC), reading only the audio."""
    part = audio_out.with_name(audio_out.name + ".part")
    command = [*_FFMPEG, "-i", str(info.path), "-map", f"0:a:{info.audio_index}"]
    command += ["-vn", "-sn", "-dn", "-ac", "1", "-ar", "16000", "-c:a", "flac", "-f", "flac"]
    try:
        error = _run([*command, str(part)], info.duration, on_progress)
        if error:
            raise RuntimeError(f"ffmpeg could not read {info.path.name}: {error.strip()[-400:]}")
        part.replace(audio_out)
    finally:
        part.unlink(missing_ok=True)


def find_shots(
    info: SourceInfo, work: Path, *, on_progress: Callable[[float], None] | None = None
) -> list[float]:
    """The times of the cuts between shots: decoded on the graphics card if it can, shrunk, and
    scored by ffmpeg's scene change detector, which lets every frame through (so the progress
    is known) and marks the cuts."""
    found = work / f".shots-{info.audio_index}.part"
    error = ""
    try:
        for gpu in (True, False):
            shrink = (
                f"scale_cuda={_SHOT_WIDTH}:-2,hwdownload,format=nv12"
                if gpu
                else f"scale={_SHOT_WIDTH}:-2"
            )
            marks = f"scdet=threshold={_SCENE_THRESHOLD},metadata=print:key=lavfi.scd.time"
            command = [*_FFMPEG]
            if gpu:
                command += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
            command += ["-i", str(info.path), "-map", "0:v:0", "-an", "-sn", "-dn"]
            command += ["-vf", f"{shrink},{marks}:file={_escape(found)}", "-f", "null", "-"]
            error = _run(command, info.duration, on_progress)
            if not error:
                return _cuts(found)
    finally:
        found.unlink(missing_ok=True)
    raise RuntimeError(f"ffmpeg could not look for cuts in {info.path.name}: {error[-400:]}")


def cache_key(info: SourceInfo, *parts: str) -> str:
    """Names the cached work for this exact file (path, size and date) and these step versions."""
    text = "|".join([str(info.path.resolve()), str(info.size), str(info.mtime_ns), *parts])
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def _run(command: list[str], duration: float, on_progress: Callable[[float], None] | None) -> str:
    """Runs ffmpeg, reporting progress from its `-progress` lines; returns stderr on failure.

    stderr goes to a temporary file, not a pipe: a damaged video makes the decoder print more
    than a pipe holds, and ffmpeg would wait on it while this waits on stdout, forever.
    """
    with tempfile.TemporaryFile() as errors:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True) as process:
            assert process.stdout is not None
            last = -1.0
            for line in process.stdout:
                key, _, value = line.strip().partition("=")
                if key == "out_time_us" and on_progress is not None and duration > 0:
                    try:
                        done = min(max(int(value) / 1e6 / duration, 0.0), 1.0)
                    except ValueError:
                        continue
                    if done > last:
                        on_progress(done)
                        last = done
        if process.returncode == 0:
            return ""
        errors.seek(0)
        tail = errors.read()[-4000:].decode(errors="replace")
        return tail or f"exit code {process.returncode}"


def _cuts(shots: Path) -> list[float]:
    if not shots.is_file():
        return []
    times = [float(m.group(1)) for m in _PTS_TIME.finditer(shots.read_text(errors="replace"))]
    return sorted(set(times))


def _escape(path: Path) -> str:
    """A path inside a filter graph: its colons, backslashes and quotes escaped."""
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _rate(text: object) -> float:
    if not isinstance(text, str) or "/" not in text:
        return 0.0
    num, den = text.split("/", 1)
    try:
        return float(num) / float(den) if float(den) else 0.0
    except ValueError:
        return 0.0
