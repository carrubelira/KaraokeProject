"""Enrolling workers, and what they ask for: leases, heartbeats, progress and results."""

import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from karaoke_contracts.nodes import (
    Capabilities,
    Enrolled,
    Enrollment,
    Heartbeat,
    Lease,
    TaskFailure,
    TaskLog,
    TaskProgress,
    TaskResult,
    Telemetry,
)
from karaoke_server.auth import Node, Operator, node, operator, worker
from karaoke_server.errors import ApiError
from karaoke_server.fleet import busy_playing, nodes, publish_node
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api", tags=["nodes"])


class NewEnrollment(BaseModel):
    kind: Literal["worker"] = "worker"


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
    publish_node(found, new.id)
    return Enrolled(node_id=new.id, credential=credential)


@router.get("/nodes")
async def list_nodes(request: Request, who: Operator = Depends(operator)) -> list[dict[str, Any]]:
    return nodes(services(request))


@router.delete("/nodes/{node_id}", status_code=204)
async def revoke(node_id: str, request: Request, who: Operator = Depends(operator)) -> Response:
    found = services(request)
    if not found.auth.revoke(node_id):
        raise ApiError(404, "not_found", "No such node")
    publish_node(found, node_id)
    return Response(status_code=204)


class Me(BaseModel):
    id: str
    kind: str
    name: str


@router.get("/nodes/me")
async def me(who: Node = Depends(node)) -> Me:
    return Me(id=who.id, kind=who.kind, name=who.name)


@router.put("/nodes/me/capabilities")
async def update_capabilities(
    body: Capabilities, request: Request, who: Node = Depends(node)
) -> Me:
    """A node says what it offers now (on every start: a new driver, new models, a new GPU)."""
    services(request).auth.update_capabilities(who, body)
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
    found.telemetry[who.id] = (time.time(), body.telemetry)
    found.db.execute("UPDATE nodes SET last_seen = ? WHERE id = ?", (time.time(), who.id))
    stop = found.queue.renew(who, body.running)
    publish_node(found, who.id)
    return HeartbeatAnswer(stop=stop, server_time=now_us())


class LeaseRequest(BaseModel):
    free_vram_mb: int | None = None
    wait: bool = True


@router.post("/worker/lease", response_model=None)
async def lease(
    body: LeaseRequest, request: Request, who: Node = Depends(worker)
) -> Lease | Response:
    found = services(request)
    found.telemetry.setdefault(who.id, (time.time(), Telemetry()))
    timeout = found.settings.lease_wait_seconds if body.wait else 0.0
    busy = busy_playing(found, who.capabilities.same_host_as_server)
    granted = await found.queue.wait_lease(who, body.free_vram_mb, timeout, busy_playing=busy)
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


class LogBody(BaseModel):
    lease_id: str
    log: TaskLog


@router.post("/tasks/{task_id}/log", status_code=204)
async def log(
    task_id: str, body: LogBody, request: Request, who: Node = Depends(worker)
) -> Response:
    """Lines the task's process wrote, for the operator to follow live."""
    services(request).queue.log(task_id, body.lease_id, who, body.log.lines)
    return Response(status_code=204)
