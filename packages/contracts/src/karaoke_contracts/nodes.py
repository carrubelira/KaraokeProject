"""Contracts v2: how workers talk to the server (plan v4 §3 and §4)."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from karaoke_contracts.doc import NonEmptyStr
from karaoke_contracts.manifest import Model, Sha256

NodeKind = Literal["worker"]
TaskKind = Literal["fetch", "analyze", "make", "package", "render"]
TaskState = Literal[
    "waiting", "held", "ready", "leased", "running", "done", "failed", "cancelled", "paused"
]


class Gpu(Model):
    name: NonEmptyStr
    vram_total_mb: Annotated[int, Field(ge=0)]


class Capabilities(Model):
    os: Literal["windows", "linux", "macos"]
    cpus: Annotated[int, Field(ge=1)] = 1
    ram_mb: Annotated[int, Field(ge=0)] = 0
    gpus: list[Gpu] = Field(default_factory=list)
    internet: bool = False
    tasks: list[TaskKind] = Field(default_factory=list, description="Task kinds it can run.")
    models: dict[str, str] = Field(default_factory=dict, description="Model name to version.")
    same_host_as_server: bool = Field(
        default=False, description="It shares the server's disk: blobs go by path, not HTTP."
    )


class Enrollment(Model):
    """Sent once with a one-time token; the answer carries the node's own credential."""

    token: NonEmptyStr
    kind: NodeKind
    name: NonEmptyStr
    capabilities: Capabilities


class Enrolled(Model):
    node_id: NonEmptyStr
    credential: NonEmptyStr


class Telemetry(Model):
    gpu_util: Annotated[float, Field(ge=0, le=100)] | None = None
    vram_used_mb: Annotated[int, Field(ge=0)] | None = None
    vram_free_mb: Annotated[int, Field(ge=0)] | None = None
    gpu_temp_c: float | None = None
    cpu_util: Annotated[float, Field(ge=0, le=100)] | None = None
    ram_used_mb: Annotated[int, Field(ge=0)] | None = None
    ram_total_mb: Annotated[int, Field(ge=0)] | None = None


class Heartbeat(Model):
    telemetry: Telemetry = Field(default_factory=Telemetry)
    running: list[NonEmptyStr] = Field(default_factory=list, description="Task ids it holds.")


class Task(Model):
    id: NonEmptyStr
    kind: TaskKind
    job_id: NonEmptyStr
    params: dict[str, Any] = Field(default_factory=dict)
    inputs: list[Sha256] = Field(default_factory=list, description="Blobs it reads.")
    vram_mb: Annotated[int, Field(ge=0)] = 0
    needs_internet: bool = False
    priority: int = 0


class Lease(Model):
    task: Task
    lease_id: NonEmptyStr
    expires_at: datetime
    heartbeat_seconds: Annotated[float, Field(gt=0)]


class TaskProgress(Model):
    stage: NonEmptyStr
    fraction: Annotated[float, Field(ge=0, le=1)] | None = None
    step: str | None = Field(default=None, description="What the stage is doing right now.")
    message: str | None = Field(default=None, description="A line for the operator.")


class TaskLog(Model):
    """Lines the task's process wrote (yt-dlp, the engine), sent in small batches."""

    lines: Annotated[list[str], Field(max_length=200)]


class TaskResult(Model):
    outputs: dict[str, Sha256] = Field(default_factory=dict, description="Named blobs it wrote.")
    data: dict[str, Any] = Field(default_factory=dict)


class TaskFailure(Model):
    code: NonEmptyStr
    message: str
    retryable: bool = True
    log: Sha256 | None = Field(default=None, description="The task's whole log, as a blob.")
