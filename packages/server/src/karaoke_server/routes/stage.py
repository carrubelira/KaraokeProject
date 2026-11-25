"""The stage (decision 011): the operator's orders, the queue, the audio routing, the screens'
settings, and the two sockets the stage talks over: the screens' (open to the LAN) and
kp-audio's (the server's own process, on the loopback)."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from karaoke_contracts.control import AudioConfig, Queue, QueueItem
from karaoke_contracts.stage import ScreenConfig, ScreenHello, Session
from karaoke_server.auth import Operator, bearer, operator, same_token
from karaoke_server.errors import ApiError
from karaoke_server.queues import new_item_id
from karaoke_server.routes._deps import services, ws_services
from karaoke_server.stage import Command

router = APIRouter(tags=["stage"])
logger = logging.getLogger(__name__)

# A screen says hello within this long of opening its socket, or it is closed.
HELLO_SECONDS = 5.0
LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}


@router.get("/api/stage")
async def view(request: Request, who: Operator = Depends(operator)) -> dict[str, Any]:
    found = services(request)
    return {**found.stage.view(), "queue": found.queues.get().model_dump(mode="json")}


class Order(BaseModel):
    command: Command
    item_id: str | None = None
    position: float | None = Field(default=None, ge=0)
    value: float | None = None
    force: bool = Field(default=False, description="Start although some screens are not ready.")


@router.post("/api/stage/commands")
async def command(body: Order, request: Request, who: Operator = Depends(operator)) -> Session:
    return services(request).stage.command(
        body.command,
        item_id=body.item_id,
        position=body.position,
        value=body.value,
        force=body.force,
    )


@router.put("/api/stage/audio")
async def set_audio(
    body: AudioConfig, request: Request, who: Operator = Depends(operator)
) -> AudioConfig:
    return services(request).stage.set_audio_config(body)


@router.get("/api/stage/queue")
async def get_queue(request: Request, who: Operator = Depends(operator)) -> Queue:
    return services(request).queues.get()


@router.put("/api/stage/queue")
async def save_queue(body: Queue, request: Request, who: Operator = Depends(operator)) -> Queue:
    """Rewrites the queue (reorder, remove, change an item) over the version it was read at."""
    found = services(request)
    library = {c["id"] for c in found.library.contents()}
    unknown = sorted({i.content_id for i in body.items} - library)
    if unknown:
        raise ApiError(422, "unknown_content", "Songs that are not in the library", ids=unknown)
    return found.queues.save(body)


class NewItem(BaseModel):
    content_id: str
    singer: str | None = Field(default=None, max_length=80)
    semitones: float = Field(default=0.0, ge=-12, le=12)


class NewItems(BaseModel):
    items: list[NewItem] = Field(min_length=1, max_length=100)
    first: bool = Field(default=False, description="Put them before everything else.")


@router.post("/api/stage/queue/items")
async def add_to_queue(
    body: NewItems, request: Request, who: Operator = Depends(operator)
) -> Queue:
    """Adds songs to the end (or the front) of the queue as it is now: no version to match."""
    found = services(request)
    for item in body.items:
        found.library.get(item.content_id)
    items = [
        QueueItem(id=new_item_id(), content_id=i.content_id, singer=i.singer,
                  semitones=i.semitones)
        for i in body.items
    ]  # fmt: skip
    return found.queues.add(items, first=body.first)


@router.put("/api/screens/{screen_id}/config")
async def set_screen_config(
    screen_id: str, body: ScreenConfig, request: Request, who: Operator = Depends(operator)
) -> ScreenConfig:
    return services(request).stage.set_screen_config(screen_id, body)


@router.delete("/api/screens/{screen_id}", status_code=204)
async def forget_screen(
    screen_id: str, request: Request, who: Operator = Depends(operator)
) -> Response:
    services(request).stage.forget_screen(screen_id)
    return Response(status_code=204)


def _screen_blob(sha256: str, request: Request) -> FileResponse:
    found = services(request)
    if sha256 not in found.stage.allowed_blobs() or not found.store.has(sha256):
        raise ApiError(404, "not_found", "No such blob on the stage")
    return FileResponse(
        found.store.path(sha256),
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, max-age=31536000, immutable", "ETag": f'"{sha256}"'},
    )


@router.get("/api/screens/blobs/{sha256}", response_class=FileResponse)
async def screen_blob(sha256: str, request: Request) -> FileResponse:
    """A blob of a song on the stage or in its queue, for any screen on the LAN; `Range`
    works, so a download resumes."""
    return _screen_blob(sha256, request)


@router.head("/api/screens/blobs/{sha256}", response_class=FileResponse)
async def screen_blob_head(sha256: str, request: Request) -> FileResponse:
    return _screen_blob(sha256, request)


@router.websocket("/api/screens/ws")
async def screen_socket(websocket: WebSocket) -> None:
    """A web screen's line: time, its settings and the session down; its state up. Open to
    the LAN (decision 011): a screen only shows what is on."""
    stage = ws_services(websocket).stage
    await websocket.accept()
    try:
        first = await asyncio.wait_for(websocket.receive_json(), HELLO_SECONDS)
        hello = ScreenHello.model_validate(first.get("hello") if isinstance(first, dict) else {})
    except (TimeoutError, ValidationError, ValueError, WebSocketDisconnect):
        await websocket.close(4400, "say hello first")
        return
    live = stage.attach_screen(websocket, hello)
    if live is None:
        await websocket.close(4009, "this screen id is already on")
        return
    try:
        while True:
            message = await websocket.receive_text()
            try:
                stage.screen_message(hello.screen_id, live, json.loads(message))
            except (ValueError, KeyError, ValidationError) as exc:
                logger.warning("bad message from screen %s: %s", hello.screen_id, exc)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        stage.detach_screen(hello.screen_id, live)
        await live.link.stop()


@router.websocket("/api/audio/ws")
async def audio_socket(websocket: WebSocket) -> None:
    """kp-audio's line: the same session as the screens, its routing and the time down; its
    state up. Only the server's own kp-audio, on the loopback, with this start's secret."""
    found = ws_services(websocket)
    host = websocket.client.host if websocket.client else ""
    # In a header: an address would put the secret in the access log.
    token = bearer(websocket.headers.get("authorization")) or ""
    if host not in LOOPBACK or not same_token(token, found.audio_token):
        await websocket.close(4401, "kp-audio only")
        return
    await websocket.accept()
    link = found.stage.attach_audio(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            try:
                found.stage.audio_message(link, json.loads(message))
            except (ValueError, KeyError, ValidationError) as exc:
                logger.warning("bad message from kp-audio: %s", exc)
            except ApiError as exc:
                logger.info("kp-audio's news changed nothing: %s", exc.detail)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        found.stage.detach_audio(link)
        await link.stop()
