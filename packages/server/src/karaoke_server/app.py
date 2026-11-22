"""The FastAPI app (plan v4 §3): API, WebSockets, blobs and the control UI, on one port."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from importlib import metadata
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from karaoke_contracts.cas import BlobStore
from karaoke_contracts.control import QueueItem
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
from karaoke_server.players import PlayerHub
from karaoke_server.queue import TaskQueue
from karaoke_server.queues import Queues, new_item_id
from karaoke_server.routes import (
    blobs,
    events,
    jobs,
    library,
    nodes,
    players,
    server,
    session,
    uploads,
    web,
)
from karaoke_server.services import Services
from karaoke_server.uploads import Uploads

logger = logging.getLogger(__name__)
# Messages sent after the request that caused them; kept so none is collected half-way.
_BACKGROUND: set[asyncio.Task[None]] = set()


def build_services(
    settings: Settings, *, db: Database | None = None, fingerprint: str = ""
) -> Services:
    settings.ensure_dirs()
    if db is None:
        db = Database(settings.db_path)
        db.migrate()
    hub = EventHub()
    store = BlobStore(settings.blobs_dir)
    content = Library(db, store, settings.trash_days)
    queues = Queues(db, hub)
    players = PlayerHub(db, hub, queues, settings.command_lead_seconds)

    def job_done(job: dict[str, Any]) -> dict[str, Any] | None:
        """A finished karaoke becomes (a new version of) a song in the library, and goes to the
        queue of the screen the operator chose when confirming it."""
        manifest = job["result"]["outputs"].get("manifest")
        if job["kind"] != "create" or manifest is None:
            return None
        registered = content.register(manifest)
        hub.publish("content", content=registered)
        player_id = job["params"].get("queue_on")
        if player_id:
            item = QueueItem(id=new_item_id(), content_id=registered["id"])
            try:
                saved = queues.add(player_id, [item])
            except ApiError:
                logger.warning("player %s is gone: %s not queued", player_id, registered["id"])
            else:
                with contextlib.suppress(RuntimeError):  # no event loop: nobody to tell now
                    sent = asyncio.get_running_loop().create_task(players.send_queue(saved))
                    _BACKGROUND.add(sent)
                    sent.add_done_callback(_BACKGROUND.discard)
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
        players=players,
        fingerprint=fingerprint,
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


def create_app(settings: Settings, *, services: Services | None = None) -> FastAPI:
    found = services or build_services(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        found.queue.start()
        tidy = asyncio.create_task(_tidy_daily(found))
        try:
            yield
        finally:
            tidy.cancel()
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
        players,
        events,
        server,
    ):
        app.include_router(module.router)
    # Last: it answers every other GET with the control UI.
    app.include_router(web.router)
    return app
