"""The interview video, read once and only read.

The video may be tens of gigabytes on a USB disk, so it is read a single time: one ffmpeg pass
writes the speech track as 16 kHz mono FLAC to the cache and, if asked, finds the cuts between
shots (scene changes on frames shrunk on the graphics card when it can). The video file is only
ever opened for reading; everything ffmpeg writes goes to the cache, under a side name that takes
its final one when the pass has finished.
"""

import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_SCENE_THRESHOLD = 0.4
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
    info: SourceInfo,
    audio_out: Path,
    *,
    shots: bool,
    on_progress: Callable[[float], None] | None = None,
) -> list[float]:
    """Writes the speech track to `audio_out` and returns the cut times (empty without shots)."""
    audio_part = audio_out.with_name(audio_out.name + ".part")
    shots_part = audio_out.with_name(audio_out.name + ".shots.part")
    attempts = (
        [_command(info, audio_part, shots_part, gpu) for gpu in (True, False)]
        if shots
        else [_command(info, audio_part, None, gpu=False)]
    )
    error = ""
    try:
        for command in attempts:
            error = _run(command, info.duration, on_progress)
            if not error:
                cuts = _cuts(shots_part) if shots else []
                audio_part.replace(audio_out)
                return cuts
    finally:
        audio_part.unlink(missing_ok=True)
        shots_part.unlink(missing_ok=True)
    raise RuntimeError(f"ffmpeg could not read {info.path.name}: {error.strip()[-400:]}")


def cache_key(info: SourceInfo, *parts: str) -> str:
    """Names the cached work for this exact file (path, size and date) and these step versions."""
    text = "|".join([str(info.path.resolve()), str(info.size), str(info.mtime_ns), *parts])
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def _command(info: SourceInfo, audio: Path, shots: Path | None, gpu: bool) -> list[str]:
    command = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-progress", "pipe:1", "-nostats"]
    if shots is not None and gpu:
        command += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
    command += ["-i", str(info.path), "-map", f"0:a:{info.audio_index}", "-vn", "-sn", "-dn"]
    command += ["-ac", "1", "-ar", "16000", "-c:a", "flac", "-f", "flac", str(audio)]
    if shots is not None:
        shrink = (
            f"scale_cuda={_SHOT_WIDTH}:-2,hwdownload,format=nv12"
            if gpu
            else f"scale={_SHOT_WIDTH}:-2"
        )
        select = f"select='gt(scene\\,{_SCENE_THRESHOLD})',metadata=print:file={_escape(shots)}"
        command += ["-map", "0:v:0", "-an", "-sn", "-dn", "-vf", f"{shrink},{select}"]
        command += ["-f", "null", "-"]
    return command


def _run(command: list[str], duration: float, on_progress: Callable[[float], None] | None) -> str:
    """Runs ffmpeg, reporting progress from its `-progress` lines; returns stderr on failure."""
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as process:
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
        stderr = process.stderr.read() if process.stderr else ""
    return "" if process.returncode == 0 else stderr or f"exit code {process.returncode}"


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
