"""Contracts v2: how workers and players talk to the server (plan v4 §3 and §4)."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from karaoke_contracts.doc import NonEmptyStr
from karaoke_contracts.manifest import ContentId, Model, Sha256

NodeKind = Literal["worker", "player"]
TaskKind = Literal["fetch", "analyze", "make", "package", "render"]
TaskState = Literal[
    "waiting", "held", "ready", "leased", "running", "done", "failed", "cancelled", "paused"
]
CacheState = Literal["absent", "downloading", "verifying", "ready", "failed"]


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
    decoders: list[str] = Field(
        default_factory=list, description="Video codecs a player decodes in hardware."
    )
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
    server_fingerprint: Annotated[str, Field(description="SHA-256 of the server certificate.")]


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
    busy_playing: bool = Field(
        default=False, description="A player on this machine is playing: go easy on the GPU."
    )


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


class Display(Model):
    id: NonEmptyStr = Field(description="Stable across reboots (EDID serial or OS id).")
    name: str
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    refresh_hz: Annotated[float, Field(gt=0)]
    primary: bool = False
    connected: bool = True


class AudioDevice(Model):
    id: NonEmptyStr = Field(description="Stable across reboots.")
    name: str
    channels: Annotated[int, Field(ge=1)] = 2
    sample_rate: Annotated[int, Field(gt=0)] = 48000
    latency_ms: Annotated[float, Field(ge=0)] | None = None
    default: bool = False
    connected: bool = True
    bluetooth: bool = False


class PlayerOutputs(Model):
    displays: list[Display] = Field(default_factory=list)
    audio: list[AudioDevice] = Field(default_factory=list)


class ContentCache(Model):
    content_id: ContentId
    manifest: Sha256
    state: CacheState
    fraction: Annotated[float, Field(ge=0, le=1)] = 0.0
    error: str | None = None


class PlayerError(Model):
    """Something the player could not do, until it can again."""

    code: Literal["output_failed", "output_lost", "display_failed", "load_failed", "master_lost"]
    device: str | None = Field(default=None, description="The audio device or display id.")
    item_id: str | None = None
    message: str


class PlayerStatus(Model):
    """What a player reports every second and on every change."""

    errors: list[PlayerError] = Field(default_factory=list)
    outputs: PlayerOutputs = Field(default_factory=PlayerOutputs)
    cache: list[ContentCache] = Field(default_factory=list)
    item_id: str | None = None
    position: float | None = None
    state: Literal["idle", "loading", "playing", "paused", "waiting"] = "idle"
    semitones: float = 0.0
    volume: float = 1.0
    sync: dict[str, float] = Field(
        default_factory=dict, description="Diagnostics: measured drift (ppm) and offsets (ms)."
    )
