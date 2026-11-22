"""Who may do what (plan v4 §3).

- **Operators** use the control UI: each has a token, made with `karaoke-server operator add`
  on the server's own console and typed once in the browser, which keeps it in an HttpOnly
  cookie. A token sent as `Authorization: Bearer` works too (scripts).
- **Nodes** (workers and players) enrol with a one-time token an operator makes; the answer is
  the node's own credential, kept by the node and sent as `Authorization: Bearer` on every
  request. A node can be revoked.

Only hashes are stored: a copied database gives no access.
"""

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Request, WebSocket

from karaoke_contracts.nodes import Capabilities, Enrollment
from karaoke_server.clock import iso_now
from karaoke_server.db import Database
from karaoke_server.errors import ApiError

COOKIE = "karaoke_session"
NodeKind = Literal["worker", "player"]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Operator:
    id: str
    name: str


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind
    name: str
    capabilities: Capabilities


class Auth:
    def __init__(self, db: Database, enrollment_hours: float = 24.0) -> None:
        self.db = db
        self.enrollment_hours = enrollment_hours

    # Operators

    def add_operator(self, name: str) -> str:
        token = "op_" + secrets.token_urlsafe(24)
        self.db.execute(
            "INSERT INTO operators (id, name, token_hash, created_at) VALUES (?, ?, ?, ?)",
            ("o_" + secrets.token_hex(6), name, _hash(token), iso_now()),
        )
        return token

    def operator(self, token: str | None) -> Operator | None:
        if not token:
            return None
        row = self.db.one("SELECT id, name FROM operators WHERE token_hash = ?", (_hash(token),))
        return Operator(row["id"], row["name"]) if row else None

    def preferences(self, operator: Operator) -> dict[str, Any]:
        row = self.db.one("SELECT preferences FROM operators WHERE id = ?", (operator.id,))
        return json.loads(row["preferences"]) if row else {}

    def set_preferences(self, operator: Operator, preferences: dict[str, Any]) -> None:
        self.db.execute(
            "UPDATE operators SET preferences = ? WHERE id = ?",
            (json.dumps(preferences, ensure_ascii=False), operator.id),
        )

    def operators(self) -> list[dict[str, str]]:
        return [dict(r) for r in self.db.query("SELECT id, name, created_at FROM operators")]

    # Nodes

    def new_enrollment(self, kind: NodeKind) -> str:
        token = f"enrol_{kind[0]}_" + secrets.token_urlsafe(18)
        self.db.execute(
            "INSERT INTO enrollments (token_hash, kind, expires_at) VALUES (?, ?, ?)",
            (_hash(token), kind, time.time() + self.enrollment_hours * 3600),
        )
        return token

    def enrol(self, request: Enrollment) -> tuple[Node, str]:
        """Spends the one-time token; returns the new node and its credential."""
        digest = _hash(request.token)
        with self.db.transaction():
            row = self.db.one("SELECT * FROM enrollments WHERE token_hash = ?", (digest,))
            if row is None or row["used_by"] is not None or row["expires_at"] < time.time():
                raise ApiError(403, "bad_enrollment", "The enrollment token is not valid")
            if row["kind"] != request.kind:
                raise ApiError(403, "bad_enrollment", f"This token enrols a {row['kind']}")
            node_id = f"{request.kind[0]}_" + secrets.token_hex(6)
            credential = "node_" + secrets.token_urlsafe(32)
            self.db.execute(
                "INSERT INTO nodes (id, kind, name, credential_hash, capabilities, created_at,"
                " last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    node_id,
                    request.kind,
                    request.name,
                    _hash(credential),
                    request.capabilities.model_dump_json(),
                    iso_now(),
                    time.time(),
                ),
            )
            self.db.execute(
                "UPDATE enrollments SET used_by = ? WHERE token_hash = ?", (node_id, digest)
            )
        return Node(node_id, request.kind, request.name, request.capabilities), credential

    def node(self, credential: str | None) -> Node | None:
        if not credential:
            return None
        row = self.db.one(
            "SELECT * FROM nodes WHERE credential_hash = ? AND revoked = 0", (_hash(credential),)
        )
        if row is None:
            return None
        return Node(
            row["id"],
            row["kind"],
            row["name"],
            Capabilities.model_validate_json(row["capabilities"]),
        )

    def update_capabilities(self, node: Node, capabilities: Capabilities) -> None:
        self.db.execute(
            "UPDATE nodes SET capabilities = ? WHERE id = ?",
            (capabilities.model_dump_json(), node.id),
        )

    def revoke(self, node_id: str) -> bool:
        return self.db.execute("UPDATE nodes SET revoked = 1 WHERE id = ?", (node_id,)) > 0


def _bearer(header: str | None) -> str | None:
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _auth(request: Request | WebSocket) -> Auth:
    auth: Auth = request.app.state.services.auth
    return auth


async def operator(request: Request) -> Operator:
    """Dependency: the operator behind a request, or 401."""
    auth = _auth(request)
    found = auth.operator(_bearer(request.headers.get("authorization"))) or auth.operator(
        request.cookies.get(COOKIE)
    )
    if found is None:
        raise ApiError(401, "unauthorized", "Sign in with an operator token")
    return found


async def node(request: Request) -> Node:
    found = _auth(request).node(_bearer(request.headers.get("authorization")))
    if found is None:
        raise ApiError(401, "unauthorized", "Unknown or revoked node")
    return found


async def worker(request: Request) -> Node:
    found = await node(request)
    if found.kind != "worker":
        raise ApiError(403, "forbidden", "Only workers may do this")
    return found


async def player(request: Request) -> Node:
    found = await node(request)
    if found.kind != "player":
        raise ApiError(403, "forbidden", "Only players may do this")
    return found


async def anyone(request: Request) -> Operator | Node:
    """An operator or a node: reading blobs."""
    auth = _auth(request)
    token = _bearer(request.headers.get("authorization"))
    found = auth.node(token) or auth.operator(token) or auth.operator(request.cookies.get(COOKIE))
    if found is None:
        raise ApiError(401, "unauthorized", "Sign in first")
    return found


def websocket_identity(websocket: WebSocket) -> Operator | Node | None:
    auth = _auth(websocket)
    token = _bearer(websocket.headers.get("authorization")) or websocket.query_params.get("token")
    return auth.node(token) or auth.operator(token) or auth.operator(websocket.cookies.get(COOKIE))


def same_token(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
