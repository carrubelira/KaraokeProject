"""Songs from a link, with yt-dlp (best effort: sites change and break it now and then).

It runs at its latest release through uvx, apart from the project's environment, so it keeps
up with the sites without anyone updating anything.
"""

import asyncio
import json
import logging
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from karaoke_worker.types import DownloadError, RemoteInfo

logger = logging.getLogger(__name__)

# Up to 1080p: the package keeps it as it came for the MP4 export (players get a 720p copy).
# The audio is the best there is.
FORMAT = "bv*[height<=1080]+ba/b[height<=1080]/b"
# Our progress lines. In --progress-template, «download:» is the kind of line, not printed text.
_PERCENT = re.compile(r"^progress\s*([\d.]+)%")


def _error(stderr: str) -> DownloadError:
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    message = lines[-1].removeprefix("ERROR: ") if lines else "The link could not be downloaded"
    if "Unsupported URL" in message or "is not a valid URL" in message:
        return DownloadError("bad_url", "That link has no song we can download")
    if "max-filesize" in message or "larger than" in message:
        return DownloadError("too_big", "The video at that link is too big")
    return DownloadError("download_failed", message[:300])


class YtDlp:
    def __init__(self, command: Sequence[str]) -> None:
        self.command = list(command)

    async def probe(self, url: str) -> RemoteInfo:
        args = [
            *self.command,
            "--dump-single-json",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            # The same choice as the download, so its files can be counted.
            "-f",
            FORMAT,
            url,
        ]
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            out, err = await asyncio.wait_for(process.communicate(), timeout=120)
        except TimeoutError as exc:
            process.kill()
            raise DownloadError("download_failed", "The site took too long to answer") from exc
        if process.returncode != 0:
            raise _error(err.decode("utf-8", "replace"))
        try:
            info = json.loads(out)
        except ValueError as exc:
            raise DownloadError("download_failed", "yt-dlp gave an answer we cannot read") from exc
        if info.get("_type") == "playlist":
            raise DownloadError("bad_url", "That is a playlist: send the link of one song")
        live = bool(info.get("is_live")) or info.get("live_status") in ("is_live", "is_upcoming")
        # The performer, when the page knows it (not the channel: that is `uploader`).
        artist = info.get("artist") or info.get("creator") or (info.get("artists") or [None])[0]
        duration = info.get("duration")
        year = info.get("release_year")
        return RemoteInfo(
            title=info.get("title"),
            artist=artist,
            track=info.get("track"),
            duration=float(duration) if duration else None,
            is_live=live,
            parts=len(info.get("requested_formats") or []) or 1,
            album=info.get("album"),
            uploader=info.get("uploader") or info.get("channel"),
            thumbnail=info.get("thumbnail"),
            year=int(year) if isinstance(year, int) else None,
        )

    async def download(
        self,
        url: str,
        dest: Path,
        on_progress: Callable[[float], None],
        parts: int = 1,
        on_line: Callable[[str], None] | None = None,
    ) -> Path:
        dest.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240 - metadata only
        args = [
            *self.command,
            "--no-playlist",
            "--newline",
            "--no-warnings",
            # --print below makes yt-dlp quiet, which hides the progress unless asked for.
            "--progress",
            "--progress-template",
            "download:progress %(progress._percent_str)s",
            "-f",
            FORMAT,
            "--max-filesize",
            "2G",
            "-o",
            str(dest / "source.%(ext)s"),
            "--print",
            "after_move:filepath",
            url,
        ]
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        assert process.stdout is not None
        assert process.stderr is not None
        stderr_task = asyncio.create_task(_lines(process.stderr, on_line))
        path: Path | None = None
        # Video and audio apart come as two files, one after the other: each fills its share.
        parts = max(1, parts)
        files, last, shown = 0, 0.0, 0.0
        try:
            async for raw in process.stdout:
                line = raw.decode("utf-8", "replace").strip()
                match = _PERCENT.match(line)
                if match:
                    percent = float(match[1]) / 100
                    if percent < last:
                        files += 1
                    last = percent
                    fraction = min(0.99, (min(files, parts - 1) + percent) / parts)
                    if fraction > shown:
                        if on_line is not None and int(fraction * 10) > int(shown * 10):
                            on_line(f"[download] {fraction:.0%}")
                        shown = fraction
                        on_progress(fraction)
                elif line and Path(line).is_absolute():
                    path = Path(line)
                elif line and on_line is not None:
                    on_line(line)
            await process.wait()
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        err = await stderr_task
        if process.returncode != 0 or path is None or not path.is_file():
            raise _error(err)
        on_progress(1.0)
        return path


async def _lines(stream: asyncio.StreamReader, on_line: Callable[[str], None] | None) -> str:
    """yt-dlp's messages, passed on as they come and kept to explain a failure."""
    kept: list[str] = []
    async for raw in stream:
        line = raw.decode("utf-8", "replace").rstrip()
        kept.append(line)
        if on_line is not None and line:
            on_line(line)
    return "\n".join(kept)
