"""What each task kind does on a worker (plan v4 §4).

- `fetch`: downloads a link with yt-dlp; the song goes up as a blob, with what the page says.
- `analyze`: works out which song it is and finds its lyrics (karaoke_worker.identify), for the
  operator to review before anything heavy runs.
- `make`: the engine makes a karaoke from the source blob, in a child process; then the package
  becomes a manifest whose blobs go up (the ones the server already has are skipped).
- `render`: the MP4 export of a manifest, in a child process.

Every task tells what it is doing through its `Feed`: stages and steps with their progress, and
the log lines of yt-dlp and the engine.
"""

import asyncio
import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_contracts import Lyrics, Manifest
from karaoke_contracts.cas import BlobStore
from karaoke_contracts.nodes import Lease, TaskResult
from karaoke_worker import identify
from karaoke_worker.child import ProcessSpawner
from karaoke_worker.client import ServerClient
from karaoke_worker.download import YtDlp
from karaoke_worker.feed import Feed
from karaoke_worker.types import DownloadError, Event

logger = logging.getLogger(__name__)

# How far each stage of `make` takes it, from the bench's timings of a 4-minute song.
MAKE_STAGES = {"decode": 0.03, "separate": 0.35, "transcribe": 0.55, "align": 0.8, "encode": 0.92}
# The analysis's steps, in order, for its progress bar.
ANALYZE_STEPS = ["metadata", "fingerprint", "acoustid", "musicbrainz", "lyrics"]


class TaskError(Exception):
    def __init__(self, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass
class Context:
    client: ServerClient
    store: BlobStore
    work: Path
    spawner: ProcessSpawner
    downloader: YtDlp
    fake: bool = False
    acoustid_key: str | None = None


def blob_path(ctx: Context, sha256: str) -> Path:
    """A local path for a blob: the server's own file when it shares this disk, else a download."""
    if ctx.store.has(sha256):
        return ctx.store.path(sha256)
    local = ctx.client.local_path(sha256)
    if local is not None:
        return local
    return ctx.client.download(sha256, ctx.store)


async def fetch_blob(ctx: Context, sha256: str) -> Path:
    return await asyncio.to_thread(blob_path, ctx, sha256)


async def upload(ctx: Context, path: Path, sha256: str | None = None) -> str:
    return await asyncio.to_thread(ctx.client.upload, path, sha256)


def place(src: Path, dest: Path) -> None:
    """`src` at `dest` without copying when the disk allows (Windows refuses plain symlinks)."""
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


async def run(ctx: Context, lease: Lease, feed: Feed) -> TaskResult:
    task = lease.task
    folder = ctx.work / task.id.replace(":", "-")
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    try:
        if task.kind == "fetch":
            return await _fetch(ctx, task.params, folder, feed)
        if task.kind == "analyze":
            return await _analyze(ctx, task.params, task.inputs, feed)
        if task.kind == "make":
            return await _make(ctx, task.params, task.inputs, folder, feed)
        if task.kind == "render":
            return await _render(ctx, task.params, folder, feed)
        raise TaskError("engine_failed", f"unknown task kind {task.kind}", retryable=False)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


async def _fetch(ctx: Context, params: dict[str, Any], folder: Path, feed: Feed) -> TaskResult:
    url = str(params["url"])
    feed.progress("download", 0.0, "probe", f"Asking {url} what it is")
    try:
        info = await ctx.downloader.probe(url)
        if info.is_live:
            raise TaskError("bad_url", "That is a live stream", retryable=False)
        feed.progress("download", 0.0, "download", info.title)
        path = await ctx.downloader.download(
            url,
            folder / "source",
            lambda fraction: feed.progress("download", fraction, "download", info.title),
            info.parts,
            feed.line,
        )
    except DownloadError as exc:
        raise TaskError(exc.code, str(exc), retryable=exc.code == "download_failed") from exc
    feed.progress("upload", 1.0, "source", path.name)
    sha = await upload(ctx, path)
    data = {"title": info.title, "artist": info.artist, "track": info.track,
            "album": info.album, "uploader": info.uploader, "thumbnail": info.thumbnail,
            "year": info.year, "duration": info.duration, "filename": path.name}  # fmt: skip
    return TaskResult(outputs={"source": sha}, data=data)


async def _analyze(
    ctx: Context, params: dict[str, Any], inputs: list[str], feed: Feed
) -> TaskResult:
    fetched = params.get("from", {}).get("fetch")
    source_sha = (fetched or {}).get("source") or inputs[0]
    feed.progress("analyze", 0.0, "metadata")
    source = await fetch_blob(ctx, source_sha)

    def note(step: str, line: str) -> None:
        index = ANALYZE_STEPS.index(step) if step in ANALYZE_STEPS else 0
        feed.progress("analyze", index / len(ANALYZE_STEPS), step, line)
        feed.line(f"[{step}] {line}")

    if ctx.fake:
        note("metadata", "Pretending (fake engine)")
        title = params.get("title") or (fetched or {}).get("title") or "Demo"
        guess = {"source": "title", "title": title, "artist": params.get("artist"),
                 "language": params.get("language") or "gl", "confidence": 0.5}  # fmt: skip
        data = {"best": guess, "candidates": [guess], "lyrics": [], "duration": None,
                "fingerprint": "skipped", "notes": ["fake"]}  # fmt: skip
        return TaskResult(data=data)
    data = await identify.analyse(source, fetched, params, note, ctx.acoustid_key)
    feed.progress("analyze", 1.0, "lyrics")
    return TaskResult(data=data)


def _engine_events(feed: Feed, stages: dict[str, float]) -> Callable[[Event], None]:
    def on_event(event: Event) -> None:
        kind = event.get("event")
        if kind == "stage":
            stage = str(event.get("stage"))
            feed.progress(stage, stages.get(stage), event.get("step"), event.get("message"))
        elif kind == "note":
            message = str(event.get("message"))
            feed.line(message)
            if feed.stage is not None:
                feed.progress(feed.stage, None, None, message)
        elif kind == "lyrics":
            feed.line(f"Lyrics from {event.get('source')}")

    return on_event


async def _make(
    ctx: Context, params: dict[str, Any], inputs: list[str], folder: Path, feed: Feed
) -> TaskResult:
    from karaoke_engine.package import build_manifest

    fetched = params.get("from", {}).get("fetch", {})
    source_sha = fetched.get("source") or inputs[0]
    filename = str(params.get("filename") or fetched.get("filename") or "source.bin")
    feed.progress("download", 0.0, "source")
    source = folder / ("source" + (Path(filename).suffix or ".bin"))
    await asyncio.to_thread(place, await fetch_blob(ctx, source_sha), source)
    out = folder / "package"
    spec = {
        "kind": "make",
        "fake": ctx.fake,
        "source": str(source),
        "out": str(out),
        "language": params.get("language") or "gl",
        "lyrics": params.get("lyrics"),
        "lrclib": bool(params.get("lrclib")),
        "title": params.get("title") or fetched.get("title") or Path(filename).stem,
        "artist": params.get("artist") or fetched.get("artist"),
    }
    outcome = await ctx.spawner.run(
        folder.name, spec, folder / "log.txt", _engine_events(feed, MAKE_STAGES), feed.line
    )
    if not outcome.ok:
        raise TaskError(outcome.code or "engine_failed", outcome.message or "", outcome.transient)
    feed.progress("upload", 0.95, "manifest")
    manifest, blob = await asyncio.to_thread(
        build_manifest, out, ctx.store, content_id=params.get("content_id")
    )
    for index, track in enumerate(manifest.tracks):
        feed.progress("upload", 0.95 + 0.05 * index / len(manifest.tracks), track.kind)
        await upload(ctx, ctx.store.path(track.blob.sha256), track.blob.sha256)
    await upload(ctx, ctx.store.path(blob.sha256), blob.sha256)
    return TaskResult(outputs={"manifest": blob.sha256}, data={"content_id": manifest.content_id})


async def _render(ctx: Context, params: dict[str, Any], folder: Path, feed: Feed) -> TaskResult:
    from karaoke_engine.package import unpack

    feed.progress("download", 0.0, "manifest")
    manifest = Manifest.model_validate_json(
        (await fetch_blob(ctx, params["manifest"])).read_bytes()
    )
    for track in manifest.tracks:
        feed.progress("download", 0.0, track.kind)
        await fetch_blob(ctx, track.blob.sha256)
    lyrics_track = manifest.track("lyrics")
    assert lyrics_track is not None
    lyrics = Lyrics.model_validate_json(
        (await fetch_blob(ctx, lyrics_track.blob.sha256)).read_bytes()
    )
    package = await asyncio.to_thread(
        unpack, manifest, lyrics, lambda sha: blob_path(ctx, sha), folder / "package"
    )
    out = folder / f"{manifest.content_id}.mp4"
    spec = {
        "kind": "export",
        "fake": ctx.fake,
        "package": str(package),
        "out": str(out),
        "theme": params.get("theme", "clasico"),
        "aspect": params.get("aspect", "16:9"),
        "vocals": params.get("vocals", 0.0),
    }
    feed.progress("render", 0.1, params.get("aspect", "16:9"))
    outcome = await ctx.spawner.run(
        folder.name, spec, folder / "log.txt", _engine_events(feed, {"render": 0.1}), feed.line
    )
    if not outcome.ok:
        raise TaskError(outcome.code or "engine_failed", outcome.message or "", outcome.transient)
    feed.progress("upload", 0.95, "video")
    sha = await upload(ctx, out)
    return TaskResult(outputs={"video": sha}, data={"filename": out.name})
