"""The FastAPI app (plan v4 §3, decision 011): API, WebSockets, blobs, the console and the
screens, on one plain HTTP port."""

import asyncio
import contextlib
import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from importlib import metadata
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from karaoke_contracts.cas import BlobStore
from karaoke_contracts.control import QueueItem
from karaoke_server.audio import AudioEngine, find_engine
from karaoke_server.auth import Auth
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    validation_error_handler,
)
from karaoke_server.events import EventHub
from karaoke_server.library import Library
from karaoke_server.queue import TaskQueue
from karaoke_server.queues import Queues, new_item_id
from karaoke_server.routes import (
    blobs,
    events,
    jobs,
    library,
    nodes,
    server,
    session,
    stage,
    uploads,
    web,
)
from karaoke_server.services import Services
from karaoke_server.stage import Stage
from karaoke_server.uploads import Uploads

logger = logging.getLogger(__name__)


def build_services(settings: Settings, *, db: Database | None = None) -> Services:
    settings.ensure_dirs()
    if db is None:
        db = Database(settings.db_path)
        db.migrate()
    hub = EventHub()
    store = BlobStore(settings.blobs_dir)
    content = Library(db, store, settings.trash_days)
    queues = Queues(db, hub)
    stage_ = Stage(
        db,
        hub,
        queues,
        content,
        audio_required=settings.audio != "off",
        go_lead_seconds=settings.go_lead_seconds,
        seek_lead_seconds=settings.seek_lead_seconds,
        upcoming=settings.upcoming,
    )

    def job_done(job: dict[str, Any]) -> dict[str, Any] | None:
        """A finished karaoke becomes (a new version of) a song in the library, and goes to the
        end of the queue if the operator asked for it when confirming it."""
        manifest = job["result"]["outputs"].get("manifest")
        if job["kind"] != "create" or manifest is None:
            return None
        registered = content.register(manifest)
        hub.publish("content", content=registered)
        if job["params"].get("add_to_queue"):
            queues.add([QueueItem(id=new_item_id(), content_id=registered["id"])])
        return {"content_id": registered["id"], "manifest": registered["manifest"]}

    return Services(
        settings=settings,
        db=db,
        events=hub,
        store=store,
        auth=Auth(db, settings.enrollment_hours),
        library=content,
        queue=TaskQueue(
            db,
            hub,
            lease_seconds=settings.lease_seconds,
            on_job_done=job_done,
            blob_exists=store.has,
        ),
        uploads=Uploads(db, settings.uploads_dir, store, settings.max_upload_bytes),
        queues=queues,
        stage=stage_,
        audio_token=settings.audio_token or "audio_" + secrets.token_urlsafe(24),
    )


async def _tidy_daily(found: Services) -> None:
    """The server may run for weeks: unfinished uploads, old trash and loose blobs go daily."""
    while True:
        try:
            found.uploads.purge()
            report = await asyncio.to_thread(found.library.collect, found.settings.quota_bytes)
            if report.deleted or report.purged_contents:
                logger.info(
                    "freed %s bytes, purged %s songs", report.freed_bytes, report.purged_contents
                )
        except Exception:
            logger.exception("could not tidy the store")
        await asyncio.sleep(86400)


def _audio_engine(found: Services) -> AudioEngine | None:
    """The kp-audio the server keeps running, unless there is to be none (`off`) or someone
    else starts it (`external`)."""
    settings = found.settings
    if settings.audio in ("off", "external"):
        return None
    executable = find_engine(settings.audio)
    if executable is None:
        found.stage.set_audio_fault(f"kp-audio not found ({settings.audio})")
        logger.warning("no kp-audio (%s): the stage cannot sound", settings.audio)
        return None
    return AudioEngine(
        executable,
        server=f"http://127.0.0.1:{settings.port}",
        token=found.audio_token,
        store=settings.blobs_dir,
        on_fault=found.stage.set_audio_fault,
    )


def create_app(settings: Settings, *, services: Services | None = None) -> FastAPI:
    found = services or build_services(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        found.queue.start()
        tidy = asyncio.create_task(_tidy_daily(found))
        engine = _audio_engine(found)
        if engine is not None:
            engine.start()
        try:
            yield
        finally:
            tidy.cancel()
            if engine is not None:
                await engine.stop()
            await found.stage.close()
            await found.queue.stop()

    app = FastAPI(
        title="Karaoke server",
        version=metadata.version("karaoke-server"),
        lifespan=lifespan,
        separate_input_output_schemas=False,
    )
    app.state.services = found
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
        return response

    for module in (
        session,
        nodes,
        blobs,
        uploads,
        library,
        jobs,
        stage,
        events,
        server,
    ):
        app.include_router(module.router)
    # Last: it answers every other GET with the control UI.
    app.include_router(web.router)
    return app
