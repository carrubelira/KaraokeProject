"""One queue per player (what it will play, in order), with optimistic versions.

Every player has a queue from the moment it is enrolled, so adding a song always has a target.
Several controls may reorder the same queue at once: a full rewrite names the version it read
and one over a newer version is refused (409) with the queue as it is now. Adding songs needs no
version: they go to the end of whatever the queue is.
"""

import json
import secrets

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

    def all(self) -> list[Queue]:
        rows = self.db.query(
            "SELECT n.id FROM nodes n WHERE n.kind = 'player' AND n.revoked = 0 ORDER BY n.name"
        )
        return [self.get(r["id"]) for r in rows]

    def get(self, player_id: str) -> Queue:
        row = self.db.one("SELECT version, items FROM queues WHERE player_id = ?", (player_id,))
        if row is None:
            player = self.db.one(
                "SELECT 1 FROM nodes WHERE id = ? AND kind = 'player'", (player_id,)
            )
            if player is None:
                raise ApiError(404, "not_found", "No such player")
            return Queue(player_id=player_id, version=0)
        return Queue(player_id=player_id, version=row["version"], items=json.loads(row["items"]))

    def save(self, queue: Queue) -> Queue:
        """Writes `queue` over the version it was read at; its version goes up by one."""
        with self.db.transaction():
            current = self.get(queue.player_id)
            if current.version != queue.version:
                raise ApiError(
                    409,
                    "version_conflict",
                    "Someone else changed this queue",
                    current=current.model_dump(mode="json"),
                )
            return self._write(queue.player_id, queue.version + 1, queue.items)

    def add(self, player_id: str, items: list[QueueItem], *, first: bool = False) -> Queue:
        """Appends (or puts first) whatever the queue holds now; never a version conflict."""
        with self.db.transaction():
            current = self.get(player_id)
            merged = items + current.items if first else current.items + items
            return self._write(player_id, current.version + 1, merged)

    def _write(self, player_id: str, version: int, items: list[QueueItem]) -> Queue:
        ids = [item.id for item in items]
        if len(ids) != len(set(ids)):
            raise ApiError(422, "duplicate_items", "Two items share an id")
        saved = Queue(player_id=player_id, version=version, items=items)
        self.db.execute(
            "INSERT INTO queues (player_id, version, items, updated_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (player_id) DO UPDATE SET version = excluded.version,"
            " items = excluded.items, updated_at = excluded.updated_at",
            (player_id, version, json.dumps([i.model_dump(mode="json") for i in items]),
             iso_now()),
        )  # fmt: skip
        self.events.publish("queue", queue=saved.model_dump(mode="json"))
        return saved

    @staticmethod
    def item(queue: Queue, item_id: str) -> QueueItem:
        for item in queue.items:
            if item.id == item_id:
                return item
        raise ApiError(404, "not_found", "No such item in the queue")
