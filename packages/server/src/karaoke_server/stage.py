"""The stage (decision 011): one per backend, its session, its screens and its audio engine.

The server sets the pace. It keeps the **session**, a versioned picture of what is on, and
pushes every version to `kp-audio` (the sound cards) and to every web screen (the picture and
the lyrics); each catches up with the newest one it got and reports its own state back.

```
idle ──cue──► cueing ──audio ready──► cued ──start (operator)──► playing ◄──► paused
                 ▲                                                  │
                 └──────────── next item ◄── ended ◄── end of song ─┘
```

Nothing plays until the operator says so: `start` from `cued` or `paused`. If a screen that
counts is not ready, `start` answers 409 with the ones missing, and the console asks before
starting anyway (`force`); a late screen joins in step. The audio engine must be ready always.

Every instant is on the server's monotonic clock (`clock.now_us`). An anchor that starts or
pauses is set `go_lead` ahead (everyone is prepared by then, so it only has to cover the LAN);
a seek while playing, `seek_lead` ahead, so the screens can look for the frame in time.
"""

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import WebSocket

from karaoke_contracts.control import Anchor, AudioConfig, Queue, QueueItem
from karaoke_contracts.manifest import Manifest
from karaoke_contracts.stage import (
    AudioStatus,
    Program,
    ScreenConfig,
    ScreenHello,
    ScreenStatus,
    Session,
)
from karaoke_server.clock import now_us
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.events import EventHub
from karaoke_server.library import Library
from karaoke_server.queues import Queues

logger = logging.getLogger(__name__)

Command = Literal["cue", "start", "pause", "seek", "next", "previous", "stop", "volume", "pitch"]

# Messages waiting for one socket; a peer that falls this far behind is dropped (it reconnects
# and gets the newest session, which is all it needs).
OUTBOX = 64
# A screen whose last status is older than this does not count when deciding who is ready.
STALE_SECONDS = 5.0


class Link:
    """One socket (a screen or kp-audio) with its own writer, so a slow peer never holds up the
    others and messages to a peer keep their order."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self._outbox: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(OUTBOX)
        self._writer = asyncio.create_task(self._write())

    def send(self, message: dict[str, Any]) -> None:
        try:
            self._outbox.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("a stage peer fell behind; dropping it")
            self.close()

    def close(self) -> None:
        with contextlib.suppress(asyncio.QueueFull):
            self._outbox.put_nowait(None)

    async def _write(self) -> None:
        try:
            while (message := await self._outbox.get()) is not None:
                await self.websocket.send_json(message)
        except (RuntimeError, OSError, ConnectionError):
            pass
        with contextlib.suppress(Exception):
            await self.websocket.close()

    async def stop(self) -> None:
        self.close()
        with contextlib.suppress(BaseException):
            await self._writer


@dataclass
class ScreenLink:
    hello: ScreenHello
    link: Link
    status: ScreenStatus = field(default_factory=lambda: ScreenStatus(state="connecting"))
    status_at: float = field(default_factory=time.monotonic)


class Stage:
    def __init__(
        self,
        db: Database,
        events: EventHub,
        queues: Queues,
        library: Library,
        *,
        audio_required: bool = True,
        go_lead_seconds: float = 0.12,
        seek_lead_seconds: float = 0.4,
        upcoming: int = 3,
    ) -> None:
        self.db = db
        self.events = events
        self.queues = queues
        self.library = library
        self.audio_required = audio_required
        self.go_lead_us = int(go_lead_seconds * 1e6)
        self.seek_lead_us = int(seek_lead_seconds * 1e6)
        self.upcoming_count = upcoming
        self.session = Session(version=0, epoch=0)
        self.audio_status = AudioStatus()
        self.audio: Link | None = None
        # Why there is no audio engine, when there is none on purpose or it cannot start.
        self.audio_fault: str | None = None
        self.screens: dict[str, ScreenLink] = {}
        self._manifests: dict[str, Manifest] = {}
        self._end_timer: asyncio.Task[None] | None = None
        queues.listeners.append(self._queue_changed)

    # What the console sees

    def view(self) -> dict[str, Any]:
        return {
            "session": self.session.model_dump(mode="json"),
            "audio": self.audio_view(),
            "screens": self.screen_views(),
        }

    def audio_view(self) -> dict[str, Any]:
        return {
            "online": self.audio is not None,
            "required": self.audio_required,
            "fault": self.audio_fault,
            "status": self.audio_status.model_dump(mode="json"),
            "config": self.audio_config().model_dump(mode="json"),
        }

    def screen_views(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM screens ORDER BY first_seen")
        return [self._screen_view(row) for row in rows]

    def _screen_view(self, row: Any) -> dict[str, Any]:
        live = self.screens.get(row["id"])
        hello = live.hello.model_dump(mode="json") if live else json.loads(row["hello"])
        return {
            "id": row["id"],
            "online": live is not None,
            "last_seen": row["last_seen"],
            "hello": hello or None,
            "config": ScreenConfig.model_validate_json(row["config"]).model_dump(mode="json"),
            "status": live.status.model_dump(mode="json") if live else None,
            "counts": live is not None and self._counts(row["id"], live),
        }

    def _publish_screen(self, screen_id: str) -> None:
        row = self.db.one("SELECT * FROM screens WHERE id = ?", (screen_id,))
        if row is None:
            self.events.publish("screen-removed", id=screen_id)
        else:
            self.events.publish("screen", screen=self._screen_view(row))

    @property
    def playing(self) -> bool:
        return self.session.state == "playing"

    # Settings

    def audio_config(self) -> AudioConfig:
        row = self.db.one("SELECT value FROM stage_settings WHERE key = 'audio'")
        return AudioConfig.model_validate_json(row["value"]) if row else AudioConfig()

    def set_audio_config(self, config: AudioConfig) -> AudioConfig:
        self.db.execute(
            "INSERT INTO stage_settings (key, value) VALUES ('audio', ?)"
            " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (config.model_dump_json(),),
        )
        if self.audio:
            self.audio.send({"type": "config", "config": config.model_dump(mode="json")})
        self.events.publish("audio", audio=self.audio_view())
        return config

    def screen_config(self, screen_id: str) -> ScreenConfig:
        row = self.db.one("SELECT config FROM screens WHERE id = ?", (screen_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such screen")
        return ScreenConfig.model_validate_json(row["config"])

    def set_screen_config(self, screen_id: str, config: ScreenConfig) -> ScreenConfig:
        self.screen_config(screen_id)
        self.db.execute(
            "UPDATE screens SET config = ? WHERE id = ?", (config.model_dump_json(), screen_id)
        )
        if live := self.screens.get(screen_id):
            live.link.send({"type": "config", "config": config.model_dump(mode="json")})
        self._publish_screen(screen_id)
        return config

    def forget_screen(self, screen_id: str) -> None:
        if screen_id in self.screens:
            raise ApiError(409, "screen_online", "Close the screen before forgetting it")
        if not self.db.execute("DELETE FROM screens WHERE id = ?", (screen_id,)):
            raise ApiError(404, "not_found", "No such screen")
        self.events.publish("screen-removed", id=screen_id)

    # Programs: a queue item with the manifest it plays

    def _manifest(self, sha256: str) -> Manifest:
        found = self._manifests.get(sha256)
        if found is None:
            found = self.library.manifest(sha256)
            self._manifests[sha256] = found  # manifests never change: their hash is their name
        return found

    def program(self, item: QueueItem) -> Program:
        sha = item.manifest or self.library.get(item.content_id)["manifest"]
        manifest = self._manifest(sha)
        return Program(item=item, manifest=sha, duration=manifest.duration)

    def _upcoming(self, queue: Queue, after: str | None) -> list[Program]:
        ids = [i.id for i in queue.items]
        start = ids.index(after) + 1 if after in ids else 0
        programs: list[Program] = []
        for item in queue.items[start:]:
            if len(programs) == self.upcoming_count:
                break
            try:
                programs.append(self.program(item))
            except ApiError:
                logger.warning("queue item %s has no song; skipped ahead", item.id)
        return programs

    def allowed_blobs(self) -> set[str]:
        """What a screen may download: the songs on and in the queue, nothing else."""
        programs: list[Program] = [*self.session.upcoming]
        if self.session.current:
            programs.append(self.session.current)
        for item in self.queues.get().items:
            with contextlib.suppress(ApiError):
                programs.append(self.program(item))
        allowed: set[str] = set()
        for program in programs:
            allowed.add(program.manifest)
            allowed.update(blob.sha256 for blob in self._manifest(program.manifest).blobs())
        return allowed

    # The session

    def _position_at(self, at: int) -> float:
        anchor = self.session.anchor
        if anchor is None:
            return 0.0
        return anchor.position + anchor.rate * max(0, at - anchor.instant) / 1e6

    def _end_position(self) -> float | None:
        current = self.session.current
        if current is None:
            return None
        end = current.item.end
        return min(end, current.duration) if end is not None else current.duration

    def _set(self, **changes: Any) -> None:
        """A new version of the session, sent to kp-audio, every screen and every console."""
        changes["version"] = self.session.version + 1
        self.session = self.session.model_copy(update=changes)
        message = {"type": "session", "session": self.session.model_dump(mode="json")}
        if self.audio:
            self.audio.send(message)
        for live in self.screens.values():
            live.link.send(message)
        self.events.publish("session", session=message["session"])
        self._schedule_end()

    def _check_cued(self) -> None:
        if self.session.state != "cueing":
            return
        if self.audio_required and self.audio is None and self.audio_fault:
            self._set(state="fault")
            return
        audio = self.audio_status
        audio_ready = not self.audio_required or (
            self.audio is not None and audio.ready and audio.epoch == self.session.epoch
        )
        if audio_ready:
            self._set(state="cued")

    def not_ready(self) -> list[str]:
        """The screens that count and are not on the cued frame (or paused on it)."""
        missing = []
        for screen_id, live in self.screens.items():
            if not self._counts(screen_id, live):
                continue
            status = live.status
            if not (status.ready and status.epoch == self.session.epoch):
                missing.append(screen_id)
        return missing

    def _counts(self, screen_id: str, live: ScreenLink) -> bool:
        """Screens the operator is warned about: shown, not the console's own preview."""
        if live.hello.preview or time.monotonic() - live.status_at > STALE_SECONDS:
            return False
        row = self.db.one("SELECT config FROM screens WHERE id = ?", (screen_id,))
        config = ScreenConfig.model_validate_json(row["config"]) if row else ScreenConfig()
        return config.layout != "off"

    def _lead(self) -> int:
        """How far ahead an anchor goes: enough for the slowest screen's round trip."""
        rtts = [s.status.sync.rtt_ms for s in self.screens.values() if s.status.sync.rtt_ms]
        slowest = max(rtts, default=0.0) * 1000
        return int(min(500_000, max(self.go_lead_us, 2 * slowest + 30_000)))

    def cue(self, item_id: str | None = None, position: float | None = None) -> Session:
        queue = self.queues.get()
        if item_id is None:
            current = self.session.current
            item_id = current.item.id if current else None
        if item_id is None:
            if not queue.items:
                raise ApiError(409, "empty_queue", "The queue is empty")
            item_id = queue.items[0].id
        item = self.queues.item(queue, item_id)
        program = self.program(item)
        start = position if position is not None else (item.start or 0.0)
        start = max(0.0, min(start, program.duration))
        self._set(
            epoch=self.session.epoch + 1,
            state="cueing",
            current=program,
            anchor=Anchor(position=start, instant=now_us(), rate=0.0),
            upcoming=self._upcoming(queue, item.id),
            semitones=item.semitones,
        )
        self._check_cued()
        return self.session

    def start(self, *, force: bool = False) -> Session:
        state = self.session.state
        if state not in ("cued", "paused"):
            raise ApiError(409, "not_cued", "Cue a song first")
        if self.audio_required and self.audio is None:
            raise ApiError(409, "audio_offline", "The audio engine is not running")
        missing = self.not_ready()
        if missing and not force:
            raise ApiError(409, "screens_not_ready", "Some screens are not ready", screens=missing)
        at = now_us() + self._lead()
        self._set(state="playing", anchor=Anchor(position=self._position_at(at), instant=at))
        return self.session

    def pause(self) -> Session:
        if self.session.state != "playing":
            raise ApiError(409, "not_playing", "Nothing is playing")
        at = now_us() + self._lead()
        self._set(
            state="paused", anchor=Anchor(position=self._position_at(at), instant=at, rate=0.0)
        )
        return self.session

    def seek(self, position: float) -> Session:
        if self.session.current is None or self.session.anchor is None:
            raise ApiError(409, "nothing_cued", "Cue a song first")
        end = self._end_position() or 0.0
        position = max(0.0, min(position, end))
        playing = self.session.state == "playing"
        at = now_us() + (self.seek_lead_us if playing else self._lead())
        self._set(anchor=Anchor(position=position, instant=at, rate=1.0 if playing else 0.0))
        return self.session

    def step(self, step: int) -> Session:
        queue = self.queues.get()
        if not queue.items:
            raise ApiError(409, "empty_queue", "The queue is empty")
        ids = [item.id for item in queue.items]
        current = self.session.current
        index = ids.index(current.item.id) + step if current and current.item.id in ids else 0
        if not 0 <= index < len(ids):
            raise ApiError(409, "end_of_queue", "There is no song there")
        return self.cue(ids[index])

    def stop(self) -> Session:
        self._set(
            epoch=self.session.epoch + 1,
            state="idle",
            current=None,
            anchor=None,
            upcoming=self._upcoming(self.queues.get(), None),
        )
        return self.session

    def set_volume(self, value: float) -> Session:
        self._set(volume=min(2.0, max(0.0, value)))
        return self.session

    def set_pitch(self, value: float) -> Session:
        self._set(semitones=min(12.0, max(-12.0, value)))
        return self.session

    def command(
        self,
        command: Command,
        *,
        item_id: str | None = None,
        position: float | None = None,
        value: float | None = None,
        force: bool = False,
    ) -> Session:
        if command == "cue":
            return self.cue(item_id, position)
        if command == "start":
            return self.start(force=force)
        if command == "pause":
            return self.pause()
        if command == "seek":
            if position is None:
                raise ApiError(422, "missing_position", "Seek needs a position")
            return self.seek(position)
        if command in ("next", "previous"):
            return self.step(1 if command == "next" else -1)
        if command == "stop":
            return self.stop()
        if value is None:
            raise ApiError(422, "missing_value", f"{command} needs a value")
        return self.set_volume(value) if command == "volume" else self.set_pitch(value)

    def _queue_changed(self, queue: Queue) -> None:
        """An edit of the queue: the item on may have changed (its exit point, its key), and
        what comes next certainly did."""
        current = self.session.current
        changes: dict[str, Any] = {}
        if current is not None:
            updated = next((i for i in queue.items if i.id == current.item.id), None)
            if updated is not None and updated != current.item:
                with contextlib.suppress(ApiError):
                    changes["current"] = self.program(updated)
                if updated.semitones != current.item.semitones:
                    changes["semitones"] = updated.semitones
        upcoming = self._upcoming(queue, current.item.id if current else None)
        if upcoming != self.session.upcoming:
            changes["upcoming"] = upcoming
        if changes:
            self._set(**changes)

    # The end of a song

    def _schedule_end(self) -> None:
        if self._end_timer is not None:
            self._end_timer.cancel()
            self._end_timer = None
        anchor, end = self.session.anchor, self._end_position()
        if self.session.state != "playing" or anchor is None or end is None:
            return
        at = anchor.instant + int(max(0.0, end - anchor.position) / max(anchor.rate, 1e-9) * 1e6)
        version = self.session.version
        with contextlib.suppress(RuntimeError):  # no event loop (a script): nobody plays
            self._end_timer = asyncio.get_running_loop().create_task(self._end_at(at, version))

    async def _end_at(self, at: int, version: int) -> None:
        await asyncio.sleep(max(0.0, (at - now_us()) / 1e6))
        if self.session.version != version:
            return
        end = self._end_position() or 0.0
        self._end_timer = None
        self._set(state="ended", anchor=Anchor(position=end, instant=at, rate=0.0))
        # The next singer gets ready; the operator gives the start.
        if self.session.upcoming:
            self.cue(self.session.upcoming[0].item.id)

    # kp-audio

    def attach_audio(self, websocket: WebSocket) -> Link:
        if self.audio is not None:
            self.audio.close()
        link = Link(websocket)
        self.audio = link
        self.audio_fault = None
        link.send({"type": "time", "now": now_us(), "sent": None})
        link.send({"type": "config", "config": self.audio_config().model_dump(mode="json")})
        link.send({"type": "session", "session": self.session.model_dump(mode="json")})
        self.events.publish("audio", audio=self.audio_view())
        if self.session.state == "fault" and self.session.current is not None:
            self._set(state="cueing")  # it is back: get the song ready again
        return link

    def detach_audio(self, link: Link) -> None:
        if self.audio is link:
            self.audio = None
            self.audio_status = AudioStatus()
            self.events.publish("audio", audio=self.audio_view())

    def audio_message(self, link: Link, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "time-request":
            link.send({"type": "time", "now": now_us(), "sent": message.get("sent")})
        elif kind == "status":
            self.audio_status = AudioStatus.model_validate(message["status"])
            self.events.publish("audio-status", status=message["status"])
            if self.playing and any(e.code == "master_lost" for e in self.audio_status.errors):
                # The master output went away and kp-audio paused: so does every screen.
                self.pause()
            self._check_cued()

    def set_audio_fault(self, fault: str | None) -> None:
        self.audio_fault = fault
        if fault and self.session.state == "cueing":
            self._set(state="fault")
        self.events.publish("audio", audio=self.audio_view())

    # Screens

    def attach_screen(self, websocket: WebSocket, hello: ScreenHello) -> ScreenLink | None:
        """A screen that said hello; None if a screen with its id is already on (the page then
        makes up another id: two tabs of one browser)."""
        if hello.screen_id in self.screens:
            return None
        live = ScreenLink(hello=hello, link=Link(websocket))
        self.screens[hello.screen_id] = live
        now = time.time()
        self.db.execute(
            "INSERT INTO screens (id, hello, first_seen, last_seen) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (id) DO UPDATE SET hello = excluded.hello,"
            " last_seen = excluded.last_seen",
            (hello.screen_id, hello.model_dump_json(), now, now),
        )
        live.link.send({"type": "time", "now": now_us(), "sent": None})
        config = self.screen_config(hello.screen_id)
        live.link.send({"type": "config", "config": config.model_dump(mode="json")})
        live.link.send({"type": "session", "session": self.session.model_dump(mode="json")})
        self._publish_screen(hello.screen_id)
        return live

    def detach_screen(self, screen_id: str, live: ScreenLink) -> None:
        if self.screens.get(screen_id) is live:
            del self.screens[screen_id]
            self.db.execute(
                "UPDATE screens SET last_seen = ? WHERE id = ?", (time.time(), screen_id)
            )
            self._publish_screen(screen_id)

    def screen_message(self, screen_id: str, live: ScreenLink, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "time-request":
            live.link.send({"type": "time", "now": now_us(), "sent": message.get("sent")})
        elif kind == "status":
            status = ScreenStatus.model_validate(message["status"])
            changed = status.state != live.status.state or status.ready != live.status.ready
            live.status, live.status_at = status, time.monotonic()
            if changed:
                self._publish_screen(screen_id)
            else:
                # Small news (progress, sync figures): without the row read for every second.
                self.events.publish(
                    "screen-status", id=screen_id, status=status.model_dump(mode="json")
                )

    # Upkeep

    async def close(self) -> None:
        if self._end_timer is not None:
            self._end_timer.cancel()
        links = [s.link for s in self.screens.values()]
        if self.audio:
            links.append(self.audio)
        await asyncio.gather(*(link.stop() for link in links), return_exceptions=True)
