"""Everything a request handler may need, built once per server and kept on `app.state`."""

from dataclasses import dataclass, field
from typing import Any

from karaoke_contracts.cas import BlobStore
from karaoke_server.auth import Auth
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.events import EventHub
from karaoke_server.library import Library
from karaoke_server.players import PlayerHub
from karaoke_server.queue import TaskQueue
from karaoke_server.queues import Queues
from karaoke_server.uploads import Uploads


@dataclass
class Services:
    settings: Settings
    db: Database
    events: EventHub
    store: BlobStore
    auth: Auth
    library: Library
    queue: TaskQueue
    uploads: Uploads
    queues: Queues
    players: PlayerHub
    # SHA-256 of the TLS certificate nodes pin ("" without TLS).
    fingerprint: str = ""
    # Last telemetry of each worker (time, telemetry, busy playing), in memory: only live use.
    telemetry: dict[str, tuple[float, Any, bool]] = field(default_factory=dict)
