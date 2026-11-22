"""Players (plan v4 §6): their sockets, configuration, status and the orders they get.

The server decides *when*: every order that starts or moves playback carries an anchor on the
server's clock, `command_lead_seconds` in the future, so the player (and later several players)
start every output on the same instant whatever the network took. A player learns the offset
between its clock and the server's from `time` messages.
"""

import asyncio
import contextlib
import json
import logging
import secrets
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from karaoke_contracts.control import Anchor, PlayerCommand, PlayerConfig, Queue
from karaoke_contracts.nodes import PlayerStatus
from karaoke_server.clock import now_us
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.events import EventHub
from karaoke_server.queues import Queues

logger = logging.getLogger(__name__)


@dataclass
class PlayerState:
    status: PlayerStatus = field(default_factory=PlayerStatus)
    online: bool = False
    item_id: str | None = None
    anchor: Anchor | None = None
    volume: float = 1.0


class PlayerHub:
    def __init__(
        self, db: Database, events: EventHub, queues: Queues, lead_seconds: float = 0.3
    ) -> None:
        self.db = db
        self.events = events
        self.queues = queues
        self.lead_us = int(lead_seconds * 1e6)
        self.states: dict[str, PlayerState] = {}
        self._sockets: dict[str, WebSocket] = {}
        self._send_lock: dict[str, asyncio.Lock] = {}

    def state(self, node_id: str) -> PlayerState:
        return self.states.setdefault(node_id, PlayerState())

    def players(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, name, capabilities, last_seen FROM nodes WHERE kind = 'player'"
            " AND revoked = 0 ORDER BY name"
        )
        return [self.view(r["id"], r["name"], r["last_seen"]) for r in rows]

    def view(self, node_id: str, name: str, last_seen: float) -> dict[str, Any]:
        state = self.state(node_id)
        return {
            "id": node_id,
            "name": name,
            "online": state.online,
            "last_seen": last_seen,
            "status": state.status.model_dump(mode="json"),
            "config": self.config(node_id).model_dump(mode="json"),
            "anchor": state.anchor.model_dump(mode="json") if state.anchor else None,
            "item_id": state.item_id,
        }

    def _require(self, node_id: str) -> None:
        if not self.db.one("SELECT 1 FROM nodes WHERE id = ? AND kind = 'player'", (node_id,)):
            raise ApiError(404, "not_found", "No such player")

    def config(self, node_id: str) -> PlayerConfig:
        row = self.db.one("SELECT config FROM nodes WHERE id = ?", (node_id,))
        data = json.loads(row["config"]) if row else {}
        return PlayerConfig.model_validate(data) if data else PlayerConfig()

    async def set_config(self, node_id: str, config: PlayerConfig) -> PlayerConfig:
        self._require(node_id)
        self.db.execute(
            "UPDATE nodes SET config = ? WHERE id = ?", (config.model_dump_json(), node_id)
        )
        await self.send(node_id, {"type": "config", "config": config.model_dump(mode="json")})
        self.events.publish("player", player_id=node_id, config=config.model_dump(mode="json"))
        return config

    # Sockets

    async def attach(self, node_id: str, websocket: WebSocket) -> None:
        old = self._sockets.get(node_id)
        if old is not None:
            with contextlib.suppress(Exception):
                await old.close(4000, "replaced")
        self._sockets[node_id] = websocket
        self._send_lock[node_id] = asyncio.Lock()
        state = self.state(node_id)
        state.online = True
        # A player that (re)connects may have restarted: what it has on is what it reports in
        # its first status, not what was ordered before.
        state.item_id = None
        state.anchor = None
        config = self.config(node_id)
        await self.send(node_id, {"type": "time", "now": now_us(), "sent": None})
        await self.send(node_id, {"type": "config", "config": config.model_dump(mode="json")})
        await self.send_queue(self.queues.get(node_id))
        self.events.publish("player", player_id=node_id, online=True)

    def detach(self, node_id: str, websocket: WebSocket) -> None:
        if self._sockets.get(node_id) is websocket:
            del self._sockets[node_id]
            self.state(node_id).online = False
            self.events.publish("player", player_id=node_id, online=False)

    async def send(self, node_id: str, message: dict[str, Any]) -> bool:
        websocket = self._sockets.get(node_id)
        if websocket is None:
            return False
        try:
            async with self._send_lock[node_id]:
                await websocket.send_json(message)
        except (RuntimeError, OSError, ConnectionError):
            logger.info("player %s went away", node_id)
            self.detach(node_id, websocket)
            return False
        return True

    async def send_queue(self, queue: Queue) -> None:
        await self.send(queue.player_id, {"type": "queue", "queue": queue.model_dump(mode="json")})

    async def receive(self, node_id: str, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "status":
            status = PlayerStatus.model_validate(message["status"])
            state = self.state(node_id)
            state.status = status
            if state.item_id is None and status.item_id is not None:
                state.item_id = status.item_id  # the song it kept through a reconnection
            self.db.execute(
                "UPDATE nodes SET last_seen = strftime('%s','now') WHERE id = ?", (node_id,)
            )
            self.events.publish(
                "player-status", player_id=node_id, status=status.model_dump(mode="json")
            )
        elif kind == "time-request":
            await self.send(node_id, {"type": "time", "now": now_us(), "sent": message.get("sent")})

    # Orders

    def _position_now(self, state: PlayerState, at: int) -> float:
        if state.anchor is None:
            return state.status.position or 0.0
        return state.anchor.position + state.anchor.rate * (at - state.anchor.instant) / 1e6

    def _start(self, node_id: str, item_id: str) -> float:
        return self.queues.item(self.queues.get(node_id), item_id).start or 0.0

    def _neighbour(self, node_id: str, step: int) -> str:
        queue = self.queues.get(node_id)
        if not queue.items:
            raise ApiError(409, "empty_queue", "The queue is empty")
        ids = [item.id for item in queue.items]
        current = self.state(node_id).item_id
        index = ids.index(current) + step if current in ids else 0
        if not 0 <= index < len(ids):
            raise ApiError(409, "end_of_queue", "There is no song there")
        return ids[index]

    async def command(
        self,
        node_id: str,
        command: str,
        *,
        item_id: str | None = None,
        position: float | None = None,
        value: float | None = None,
    ) -> PlayerCommand:
        self._require(node_id)
        state = self.state(node_id)
        at = now_us() + self.lead_us
        anchor: Anchor | None = None
        if command in ("next", "previous"):
            item_id = self._neighbour(node_id, 1 if command == "next" else -1)
            command_name = "load"
            start = self._start(node_id, item_id)
            anchor = Anchor(position=start, instant=at, rate=1.0)
        elif command == "load":
            item_id = item_id or self._neighbour(node_id, 0)
            start = self._start(node_id, item_id)
            anchor = Anchor(
                position=position if position is not None else start, instant=at, rate=0.0
            )
            command_name = "load"
        elif command == "play":
            if item_id is not None and item_id != state.item_id:
                start = self._start(node_id, item_id)
                anchor = Anchor(
                    position=position if position is not None else start, instant=at, rate=1.0
                )
                command_name = "load"
            else:
                item_id = state.item_id
                if item_id is None:
                    raise ApiError(409, "nothing_loaded", "Load a song first")
                anchor = Anchor(
                    position=position if position is not None else self._position_now(state, at),
                    instant=at,
                    rate=1.0,
                )
                command_name = "play"
        elif command == "pause":
            item_id = state.item_id
            anchor = Anchor(position=self._position_now(state, at), instant=at, rate=0.0)
            command_name = "pause"
        elif command == "seek":
            if position is None:
                raise ApiError(422, "missing_position", "Seek needs a position")
            item_id = state.item_id
            rate = state.anchor.rate if state.anchor else 0.0
            anchor = Anchor(position=max(0.0, position), instant=at, rate=rate)
            command_name = "seek"
        elif command in ("volume", "pitch"):
            if value is None:
                raise ApiError(422, "missing_value", f"{command} needs a value")
            if command == "volume":
                value = min(2.0, max(0.0, value))
                state.volume = value
            else:
                value = min(12.0, max(-12.0, value))
            item_id = state.item_id
            command_name = command
        elif command in ("stop", "reload"):
            command_name = command
            item_id = None if command == "stop" else state.item_id
        else:
            raise ApiError(422, "bad_command", f"Unknown command {command}")
        order = PlayerCommand(
            id="c_" + secrets.token_hex(5),
            command=command_name,  # type: ignore[arg-type]
            item_id=item_id,
            anchor=anchor,
            value=value,
            issued_at=now_us(),
        )
        if command_name in ("load", "play", "pause", "seek"):
            state.item_id = item_id
            state.anchor = anchor
        elif command_name == "stop":
            state.item_id = None
            state.anchor = None
        delivered = await self.send(
            node_id, {"type": "command", "command": order.model_dump(mode="json")}
        )
        if not delivered:
            raise ApiError(409, "player_offline", "The player is not connected")
        self.events.publish(
            "player-command", player_id=node_id, command=order.model_dump(mode="json")
        )
        return order
