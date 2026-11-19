"""Production playlists (plan v4 §7) with optimistic versioning.

Several controls may edit the same list at once: every write names the version it read, and a
write over a newer version is refused (409) with the list as it is now, so the control merges
and tries again instead of silently undoing someone else's change.
"""

import secrets
from typing import Any

from karaoke_contracts.control import Playlist
from karaoke_server.clock import iso_now
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.events import EventHub


class Playlists:
    def __init__(self, db: Database, events: EventHub) -> None:
        self.db = db
        self.events = events

    def all(self) -> list[Playlist]:
        rows = self.db.query("SELECT data FROM playlists ORDER BY name COLLATE NOCASE")
        return [Playlist.model_validate_json(r["data"]) for r in rows]

    def get(self, playlist_id: str) -> Playlist:
        row = self.db.one("SELECT data FROM playlists WHERE id = ?", (playlist_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such playlist")
        return Playlist.model_validate_json(row["data"])

    def create(self, name: str, player_id: str | None = None) -> Playlist:
        playlist = Playlist(
            id="p_" + secrets.token_hex(5), name=name, version=1, player_id=player_id
        )
        self.db.execute(
            "INSERT INTO playlists (id, name, version, data, updated_at) VALUES (?, ?, ?, ?, ?)",
            (playlist.id, name, 1, playlist.model_dump_json(), iso_now()),
        )
        self.events.publish("playlist", playlist=playlist.model_dump(mode="json"))
        return playlist

    def save(self, playlist: Playlist) -> Playlist:
        """Writes `playlist` over the version it was read at; its version goes up by one."""
        with self.db.transaction():
            current = self.get(playlist.id)
            if current.version != playlist.version:
                raise ApiError(
                    409,
                    "version_conflict",
                    "Someone else changed this playlist",
                    current=current.model_dump(mode="json"),
                )
            ids = [item.id for item in playlist.items]
            if len(ids) != len(set(ids)):
                raise ApiError(422, "duplicate_items", "Two items share an id")
            saved = playlist.model_copy(update={"version": playlist.version + 1})
            self.db.execute(
                "UPDATE playlists SET name = ?, version = ?, data = ?, updated_at = ? WHERE id = ?",
                (saved.name, saved.version, saved.model_dump_json(), iso_now(), saved.id),
            )
        self.events.publish("playlist", playlist=saved.model_dump(mode="json"))
        return saved

    def delete(self, playlist_id: str) -> None:
        if not self.db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,)):
            raise ApiError(404, "not_found", "No such playlist")
        self.events.publish("playlist-deleted", id=playlist_id)

    def item(self, playlist: Playlist, item_id: str) -> Any:
        for item in playlist.items:
            if item.id == item_id:
                return item
        raise ApiError(404, "not_found", "No such item in the playlist")
