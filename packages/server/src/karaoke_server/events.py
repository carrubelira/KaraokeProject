"""Live state for the control UI: every change is one JSON event pushed to each open socket.

Each subscriber has its own bounded queue; a control that stops reading is dropped rather than
let the queue grow, and reconnects (it then reloads the state it shows).
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)

Event = dict[str, Any]


class EventHub:
    def __init__(self, depth: int = 256) -> None:
        self._subscribers: set[asyncio.Queue[Event | None]] = set()
        self._depth = depth
        self.sequence = 0

    def publish(self, kind: str, **data: Any) -> None:
        self.sequence += 1
        event = {"type": kind, "seq": self.sequence, **data}
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("a control fell behind; dropping it")
                self._subscribers.discard(queue)
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(None)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator["asyncio.Queue[Event | None]"]:
        queue: asyncio.Queue[Event | None] = asyncio.Queue(self._depth)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    @property
    def subscribers(self) -> int:
        return len(self._subscribers)
