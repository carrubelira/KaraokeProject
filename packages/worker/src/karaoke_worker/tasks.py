"""What each task kind does on a worker (plan v4 §4).

- `fetch`: downloads a link with yt-dlp; the song goes up as a blob.
- `make`: the engine makes a karaoke from the source blob, in a child process; then the package
  becomes a manifest whose blobs go up (the ones the server already has are skipped).
- `render`: the MP4 export of a manifest, in a child process.
"""

import asyncio
import logging
import os
import shutil
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_contracts import Lyrics, Manifest
from karaoke_contracts.cas import BlobStore
from karaoke_contracts.nodes import Lease, TaskProgress, TaskResult
from karaoke_worker.child import ProcessSpawner
from karaoke_worker.client import ServerClient
from karaoke_worker.download import YtDlp
from karaoke_worker.types import DownloadError, Event

logger = logging.getLogger(__name__)

# How far each stage of `make` takes it, from the bench's timings of a 4-minute song.
MAKE_STAGES = {"decode": 0.03, "separate": 0.35, "transcribe": 0.55, "align": 0.8, "encode": 0.92}

Report = Callable[[TaskProgress], Coroutine[Any, Any, None]]
# Progress reports sent in the background; kept here so none is collected half-way.
_PENDING: set["asyncio.Task[None]"] = set()


def _send(loop: asyncio.AbstractEventLoop, coroutine: Coroutine[Any, Any, None]) -> None:
    task = loop.create_task(coroutine)
    _PENDING.add(task)
    task.add_done_callback(_PENDING.discard)


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


async def run(ctx: Context, lease: Lease, report: Report) -> TaskResult:
    task = lease.task
    folder = ctx.work / task.id.replace(":", "-")
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    try:
        if task.kind == "fetch":
            return await _fetch(ctx, task.params, folder, report)
        if task.kind == "make":
            return await _make(ctx, task.params, task.inputs, folder, report)
        if task.kind == "render":
            return await _render(ctx, task.params, folder, report)
        raise TaskError("engine_failed", f"unknown task kind {task.kind}", retryable=False)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


async def _fetch(ctx: Context, params: dict[str, Any], folder: Path, report: Report) -> TaskResult:
    url = str(params["url"])
    loop = asyncio.get_running_loop()

    def progress(fraction: float) -> None:
        _send(loop, report(TaskProgress(stage="download", fraction=min(1.0, fraction))))

    try:
        info = await ctx.downloader.probe(url)
        if info.is_live:
            raise TaskError("bad_url", "That is a live stream", retryable=False)
        path = await ctx.downloader.download(url, folder / "source", progress, info.parts)
    except DownloadError as exc:
        raise TaskError(exc.code, str(exc), retryable=exc.code == "download_failed") from exc
    await report(TaskProgress(stage="upload", fraction=1.0))
    sha = await upload(ctx, path)
    data = {"title": info.title, "artist": info.artist or info.track, "duration": info.duration,
            "filename": path.name}  # fmt: skip
    return TaskResult(outputs={"source": sha}, data=data)


def _on_stage(report: Report) -> Callable[[Event], None]:
    loop = asyncio.get_running_loop()

    def on_event(event: Event) -> None:
        if event.get("event") == "stage":
            stage = str(event.get("stage"))
            _send(loop, report(TaskProgress(stage=stage, fraction=MAKE_STAGES.get(stage))))
        elif event.get("event") == "note":
            logger.info("%s", event.get("message"))

    return on_event


async def _make(
    ctx: Context, params: dict[str, Any], inputs: list[str], folder: Path, report: Report
) -> TaskResult:
    from karaoke_engine.package import build_manifest

    fetched = params.get("from", {}).get("fetch", {})
    source_sha = fetched.get("source") or inputs[0]
    filename = str(params.get("filename") or fetched.get("filename") or "source.bin")
    await report(TaskProgress(stage="download", fraction=0.0))
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
    outcome = await ctx.spawner.run(folder.name, spec, folder / "log.txt", _on_stage(report))
    if not outcome.ok:
        raise TaskError(outcome.code or "engine_failed", outcome.message or "", outcome.transient)
    await report(TaskProgress(stage="upload", fraction=0.95))
    manifest, blob = await asyncio.to_thread(
        build_manifest, out, ctx.store, content_id=params.get("content_id")
    )
    for track in manifest.tracks:
        await upload(ctx, ctx.store.path(track.blob.sha256), track.blob.sha256)
    await upload(ctx, ctx.store.path(blob.sha256), blob.sha256)
    return TaskResult(outputs={"manifest": blob.sha256}, data={"content_id": manifest.content_id})


async def _render(ctx: Context, params: dict[str, Any], folder: Path, report: Report) -> TaskResult:
    from karaoke_engine.package import unpack

    await report(TaskProgress(stage="download", fraction=0.0))
    manifest = Manifest.model_validate_json(
        (await fetch_blob(ctx, params["manifest"])).read_bytes()
    )
    for track in manifest.tracks:
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
    await report(TaskProgress(stage="render", fraction=0.1))
    outcome = await ctx.spawner.run(folder.name, spec, folder / "log.txt", _on_stage(report))
    if not outcome.ok:
        raise TaskError(outcome.code or "engine_failed", outcome.message or "", outcome.transient)
    await report(TaskProgress(stage="upload", fraction=0.95))
    sha = await upload(ctx, out)
    return TaskResult(outputs={"video": sha}, data={"filename": out.name})
