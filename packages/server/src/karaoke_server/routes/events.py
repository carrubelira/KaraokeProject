"""The control UI's live line: a snapshot on connect, then every change as it happens."""

import asyncio
import contextlib
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from karaoke_server.auth import Operator, websocket_identity
from karaoke_server.clock import now_us
from karaoke_server.routes._deps import ws_services
from karaoke_server.services import Services

router = APIRouter(tags=["events"])


def snapshot(found: Services) -> dict[str, Any]:
    return {
        "type": "snapshot",
        "seq": found.events.sequence,
        "now": now_us(),
        "jobs": found.queue.jobs(limit=100),
        "contents": found.library.contents(),
        "playlists": [p.model_dump(mode="json") for p in found.playlists.all()],
        "players": found.players.players(),
    }


@router.websocket("/api/events")
async def control_socket(websocket: WebSocket) -> None:
    who = websocket_identity(websocket)
    if not isinstance(who, Operator):
        await websocket.close(4401, "operators only")
        return
    found = ws_services(websocket)
    await websocket.accept()
    async with found.events.subscribe() as queue:
        await websocket.send_json(snapshot(found))
        reader = asyncio.create_task(_drain(websocket))
        try:
            while True:
                getter = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait({getter, reader}, return_when=asyncio.FIRST_COMPLETED)
                if reader in done:
                    getter.cancel()
                    break
                event = getter.result()
                if event is None:
                    await websocket.close(4008, "too slow")
                    break
                await websocket.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            reader.cancel()
            with contextlib.suppress(BaseException):
                await reader


async def _drain(websocket: WebSocket) -> None:
    """Reads (and ignores) what the control sends, to notice when it goes away; answers pings."""
    with contextlib.suppress(WebSocketDisconnect, RuntimeError):
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict) and message.get("type") == "ping":
                await websocket.send_json(
                    {"type": "pong", "now": now_us(), "sent": message.get("sent")}
                )
