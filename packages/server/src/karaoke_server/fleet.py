"""How the control sees the enrolled nodes: what each offers, whether it answers, what it runs."""

import json
import time
from typing import Any

from karaoke_contracts.nodes import Telemetry
from karaoke_server.services import Services


def node_view(found: Services, row: Any) -> dict[str, Any]:
    seen, telemetry, busy = found.telemetry.get(row["id"], (row["last_seen"], Telemetry(), False))
    running = [
        t["id"]
        for t in found.db.query(
            "SELECT id FROM tasks WHERE node_id = ? AND state IN ('leased', 'running')",
            (row["id"],),
        )
    ]
    if row["kind"] == "player":
        online = found.players.state(row["id"]).online
    else:
        online = time.time() - seen < 3 * found.settings.lease_seconds
    return {
        "id": row["id"],
        "kind": row["kind"],
        "name": row["name"],
        "capabilities": json.loads(row["capabilities"]),
        "last_seen": seen,
        "online": online,
        "telemetry": telemetry.model_dump(mode="json"),
        "busy_playing": busy,
        "running": running,
    }


def nodes(found: Services) -> list[dict[str, Any]]:
    rows = found.db.query("SELECT * FROM nodes WHERE revoked = 0 ORDER BY kind, name")
    return [node_view(found, row) for row in rows]


def publish_node(found: Services, node_id: str) -> None:
    """Sends the node as it is now to every control (enrolled, a heartbeat, a lease, revoked)."""
    row = found.db.one("SELECT * FROM nodes WHERE id = ?", (node_id,))
    if row is None or row["revoked"]:
        found.events.publish("node-removed", id=node_id)
    else:
        found.events.publish("node", node=node_view(found, row))
