"""Players: their outputs and settings, the orders operators give, and their own socket."""

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from karaoke_contracts.control import PlayerCommand, PlayerConfig
from karaoke_server.auth import Node, Operator, operator, websocket_identity
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
    """The player's line to the server: config, playlist and orders down; status up."""
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
