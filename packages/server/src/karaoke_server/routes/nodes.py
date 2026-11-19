"""Enrolling nodes, and what workers ask for: leases, heartbeats, progress and results."""

import json
import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from karaoke_contracts.nodes import (
    Enrolled,
    Enrollment,
    Heartbeat,
    Lease,
    TaskFailure,
    TaskProgress,
    TaskResult,
    Telemetry,
)
from karaoke_server.auth import Node, Operator, node, operator, worker
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api", tags=["nodes"])


class NewEnrollment(BaseModel):
    kind: Literal["worker", "player"]


class EnrollmentToken(BaseModel):
    token: str
    kind: str
    expires_in_hours: float


@router.post("/enrollments")
async def new_enrollment(
    body: NewEnrollment, request: Request, who: Operator = Depends(operator)
) -> EnrollmentToken:
    found = services(request)
    return EnrollmentToken(
        token=found.auth.new_enrollment(body.kind),
        kind=body.kind,
        expires_in_hours=found.settings.enrollment_hours,
    )


@router.post("/nodes/enroll")
async def enroll(body: Enrollment, request: Request) -> Enrolled:
    found = services(request)
    new, credential = found.auth.enrol(body)
    found.events.publish("node", node={"id": new.id, "kind": new.kind, "name": new.name})
    return Enrolled(node_id=new.id, credential=credential, server_fingerprint=found.fingerprint)


@router.get("/nodes")
async def list_nodes(request: Request, who: Operator = Depends(operator)) -> list[dict[str, Any]]:
    found = services(request)
    rows = found.db.query("SELECT * FROM nodes WHERE revoked = 0 ORDER BY kind, name")
    out = []
    for row in rows:
        seen, telemetry, busy = found.telemetry.get(
            row["id"], (row["last_seen"], Telemetry(), False)
        )
        running = [
            t["id"]
            for t in found.db.query(
                "SELECT id FROM tasks WHERE node_id = ? AND state IN ('leased', 'running')",
                (row["id"],),
            )
        ]
        out.append(
            {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "capabilities": json.loads(row["capabilities"]),
                "last_seen": seen,
                "online": time.time() - seen < 3 * found.settings.lease_seconds
                or (row["kind"] == "player" and found.players.state(row["id"]).online),
                "telemetry": telemetry.model_dump(mode="json"),
                "busy_playing": busy,
                "running": running,
            }
        )
    return out


@router.delete("/nodes/{node_id}", status_code=204)
async def revoke(node_id: str, request: Request, who: Operator = Depends(operator)) -> Response:
    if not services(request).auth.revoke(node_id):
        raise ApiError(404, "not_found", "No such node")
    return Response(status_code=204)


class Me(BaseModel):
    id: str
    kind: str
    name: str


@router.get("/nodes/me")
async def me(who: Node = Depends(node)) -> Me:
    return Me(id=who.id, kind=who.kind, name=who.name)


class HeartbeatAnswer(BaseModel):
    stop: list[str]
    server_time: int


@router.post("/worker/heartbeat")
async def heartbeat(
    body: Heartbeat, request: Request, who: Node = Depends(worker)
) -> HeartbeatAnswer:
    from karaoke_server.clock import now_us

    found = services(request)
    found.telemetry[who.id] = (time.time(), body.telemetry, body.busy_playing)
    found.db.execute("UPDATE nodes SET last_seen = ? WHERE id = ?", (time.time(), who.id))
    found.events.publish(
        "telemetry", node_id=who.id, telemetry=body.telemetry.model_dump(mode="json"),
        busy_playing=body.busy_playing,
    )  # fmt: skip
    return HeartbeatAnswer(stop=found.queue.renew(who, body.running), server_time=now_us())


class LeaseRequest(BaseModel):
    free_vram_mb: int | None = None
    busy_playing: bool = False
    wait: bool = True


@router.post("/worker/lease", response_model=None)
async def lease(
    body: LeaseRequest, request: Request, who: Node = Depends(worker)
) -> Lease | Response:
    found = services(request)
    found.telemetry.setdefault(who.id, (time.time(), Telemetry(), body.busy_playing))
    timeout = found.settings.lease_wait_seconds if body.wait else 0.0
    granted = await found.queue.wait_lease(
        who, body.free_vram_mb, timeout, busy_playing=body.busy_playing
    )
    if granted is None:
        return Response(status_code=204)
    return granted


class ProgressBody(BaseModel):
    lease_id: str
    progress: TaskProgress


class ProgressAnswer(BaseModel):
    keep_going: bool


@router.post("/tasks/{task_id}/progress")
async def progress(
    task_id: str, body: ProgressBody, request: Request, who: Node = Depends(worker)
) -> ProgressAnswer:
    return ProgressAnswer(
        keep_going=services(request).queue.progress(task_id, body.lease_id, who, body.progress)
    )


class CompleteBody(BaseModel):
    lease_id: str
    result: TaskResult


@router.post("/tasks/{task_id}/complete", status_code=204)
async def complete(
    task_id: str, body: CompleteBody, request: Request, who: Node = Depends(worker)
) -> Response:
    services(request).queue.complete(task_id, body.lease_id, who, body.result)
    return Response(status_code=204)


class FailBody(BaseModel):
    lease_id: str
    failure: TaskFailure


@router.post("/tasks/{task_id}/fail", status_code=204)
async def fail(
    task_id: str, body: FailBody, request: Request, who: Node = Depends(worker)
) -> Response:
    services(request).queue.fail(task_id, body.lease_id, who, body.failure)
    return Response(status_code=204)
