"""The stage's queue (what it will play, in order), with optimistic versions (decision 011).

There is one per backend. Several consoles may reorder it at once: a full rewrite names the
version it read and one over a newer version is refused (409) with the queue as it is now.
Adding songs needs no version: they go to the end (or the front) of whatever the queue is.
"""

import json
import secrets
from collections.abc import Callable

from karaoke_contracts.control import Queue, QueueItem
from karaoke_server.clock import iso_now
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.events import EventHub


def new_item_id() -> str:
    return "i_" + secrets.token_hex(5)


class Queues:
    def __init__(self, db: Database, events: EventHub) -> None:
        self.db = db
        self.events = events
        # Told after every write (the stage refreshes what comes next).
        self.listeners: list[Callable[[Queue], None]] = []

    def get(self) -> Queue:
        row = self.db.one("SELECT version, items FROM queue WHERE id = 1")
        if row is None:
            return Queue(version=0)
        return Queue(version=row["version"], items=json.loads(row["items"]))

    def save(self, queue: Queue) -> Queue:
        """Writes `queue` over the version it was read at; its version goes up by one."""
        with self.db.transaction():
            current = self.get()
            if current.version != queue.version:
                raise ApiError(
                    409,
                    "version_conflict",
                    "Someone else changed the queue",
                    current=current.model_dump(mode="json"),
                )
            return self._write(queue.version + 1, queue.items)

    def add(self, items: list[QueueItem], *, first: bool = False) -> Queue:
        """Appends (or puts first) whatever the queue holds now; never a version conflict."""
        with self.db.transaction():
            current = self.get()
            merged = items + current.items if first else current.items + items
            return self._write(current.version + 1, merged)

    def _write(self, version: int, items: list[QueueItem]) -> Queue:
        ids = [item.id for item in items]
        if len(ids) != len(set(ids)):
            raise ApiError(422, "duplicate_items", "Two items share an id")
        saved = Queue(version=version, items=items)
        self.db.execute(
            "INSERT INTO queue (id, version, items, updated_at) VALUES (1, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET version = excluded.version,"
            " items = excluded.items, updated_at = excluded.updated_at",
            (version, json.dumps([i.model_dump(mode="json") for i in items]), iso_now()),
        )
        self.events.publish("queue", queue=saved.model_dump(mode="json"))
        for listener in self.listeners:
            listener(saved)
        return saved

    @staticmethod
    def item(queue: Queue, item_id: str) -> QueueItem:
        for item in queue.items:
            if item.id == item_id:
                return item
        raise ApiError(404, "not_found", "No such item in the queue")
