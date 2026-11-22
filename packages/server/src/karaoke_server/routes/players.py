"""Players: their outputs and settings, their queue, the orders operators give, and their
own socket."""

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from karaoke_contracts.control import PlayerCommand, PlayerConfig, Queue, QueueItem
from karaoke_server.auth import Node, Operator, operator, websocket_identity
from karaoke_server.errors import ApiError
from karaoke_server.queues import new_item_id
from karaoke_server.routes._deps import services, ws_services

router = APIRouter(prefix="/api/players", tags=["players"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_players(request: Request, who: Operator = Depends(operator)) -> list[dict[str, Any]]:
    return services(request).players.players()


@router.put("/{player_id}/config")
async def set_config(
    player_id: str, body: PlayerConfig, request: Request, who: Operator = Depends(operator)
) -> PlayerConfig:
    return await services(request).players.set_config(player_id, body)


@router.get("/{player_id}/queue")
async def get_queue(player_id: str, request: Request, who: Operator = Depends(operator)) -> Queue:
    return services(request).queues.get(player_id)


@router.put("/{player_id}/queue")
async def save_queue(
    player_id: str, body: Queue, request: Request, who: Operator = Depends(operator)
) -> Queue:
    """Rewrites the queue (reorder, remove, change an item) over the version it was read at."""
    if body.player_id != player_id:
        raise ApiError(422, "id_mismatch", "The body is another player's queue")
    found = services(request)
    library = {c["id"] for c in found.library.contents()}
    unknown = sorted({i.content_id for i in body.items} - library)
    if unknown:
        raise ApiError(422, "unknown_content", "Songs that are not in the library", ids=unknown)
    saved = found.queues.save(body)
    await found.players.send_queue(saved)
    return saved


class NewItem(BaseModel):
    content_id: str
    singer: str | None = Field(default=None, max_length=80)
    semitones: float = Field(default=0.0, ge=-12, le=12)


class NewItems(BaseModel):
    items: list[NewItem] = Field(min_length=1, max_length=100)
    first: bool = Field(default=False, description="Put them before everything else.")


@router.post("/{player_id}/queue/items")
async def add_to_queue(
    player_id: str, body: NewItems, request: Request, who: Operator = Depends(operator)
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
    saved = found.queues.add(player_id, items, first=body.first)
    await found.players.send_queue(saved)
    return saved


class Order(BaseModel):
    command: Literal[
        "load", "play", "pause", "seek", "next", "previous", "stop", "volume", "pitch", "reload"
    ]
    item_id: str | None = None
    position: float | None = Field(default=None, ge=0)
    value: float | None = None


@router.post("/{player_id}/commands")
async def command(
    player_id: str, body: Order, request: Request, who: Operator = Depends(operator)
) -> PlayerCommand:
    return await services(request).players.command(
        player_id, body.command, item_id=body.item_id, position=body.position, value=body.value
    )


@router.websocket("/ws")
async def player_socket(websocket: WebSocket) -> None:
    """The player's line to the server: config, queue and orders down; status up."""
    who = websocket_identity(websocket)
    if not isinstance(who, Node) or who.kind != "player":
        await websocket.close(4401, "players only")
        return
    hub = ws_services(websocket).players
    await websocket.accept()
    await hub.attach(who.id, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            try:
                await hub.receive(who.id, json.loads(message))
            except (ValueError, KeyError) as exc:
                logger.warning("bad message from player %s: %s", who.id, exc)
    except WebSocketDisconnect:
        pass
    finally:
        hub.detach(who.id, websocket)
