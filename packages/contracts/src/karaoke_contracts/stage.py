"""Contracts v2: the stage, its screens and its audio engine (decision 011).

The server publishes the **session**: a declarative, versioned picture of what is on (the item,
its manifest, the anchor that says where the song is at which instant). `kp-audio` and every
web screen catch up with the newest version they get, so starting, reconnecting and joining in
the middle of a song are the same path. Each of them reports its own state back.
"""

from typing import Annotated, Literal

from pydantic import Field

from karaoke_contracts.control import Anchor, QueueItem
from karaoke_contracts.doc import NonEmptyStr
from karaoke_contracts.manifest import ContentId, Model, Sha256

SessionState = Literal["idle", "cueing", "cued", "playing", "paused", "ended", "fault"]
ScreenState = Literal[
    "connecting", "idle", "provisioning", "syncing", "waiting", "playing", "paused", "error"
]
ScreenFlag = Literal["offline", "hidden", "degraded", "fullscreen"]
ScreenLayout = Literal["video-lyrics", "lyrics", "video", "off"]
CacheState = Literal["absent", "downloading", "verifying", "ready", "failed"]
AudioState = Literal["idle", "loading", "ready", "playing", "paused"]
VideoCodec = Literal["h264", "hevc", "av1"]


class Program(Model):
    """A queue item with the manifest it plays: what screens and audio prepare."""

    item: QueueItem
    manifest: Sha256
    duration: Annotated[float, Field(gt=0)]


class Session(Model):
    version: Annotated[int, Field(ge=0)] = Field(description="Goes up on every change.")
    epoch: Annotated[int, Field(ge=0)] = Field(
        description="Goes up on every cue; `ready` reports name the epoch they are for."
    )
    state: SessionState = "idle"
    current: Program | None = None
    anchor: Anchor | None = Field(default=None, description="Where the song is, and when.")
    upcoming: list[Program] = Field(
        default_factory=list, description="The next items, to download and get ready ahead."
    )
    semitones: Annotated[float, Field(ge=-12, le=12)] = 0.0
    volume: Annotated[float, Field(ge=0, le=2)] = 1.0


class ContentCache(Model):
    content_id: ContentId
    manifest: Sha256
    state: CacheState
    fraction: Annotated[float, Field(ge=0, le=1)] = 0.0
    error: str | None = None


class ScreenConfig(Model):
    """What the operator sets for one screen, kept by its id."""

    name: str | None = None
    layout: ScreenLayout = "video-lyrics"
    theme: str = "clasico"
    display_ms: Annotated[float, Field(ge=-500, le=2000)] = Field(
        default=0.0, description="How late the picture really is (the TV's processing)."
    )
    video_max_height: Annotated[int, Field(gt=0)] | None = Field(
        default=None, description="Never download a taller video than this (a Raspberry Pi)."
    )


class ScreenHello(Model):
    """The first thing a screen says: who it is and what it can show."""

    screen_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,64}$")]
    agent: str = Field(default="", max_length=300, description="The browser's user agent.")
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    refresh_hz: Annotated[float, Field(gt=0)] | None = None
    codecs: list[VideoCodec] = Field(default_factory=lambda: list[VideoCodec](["h264"]))
    preview: bool = Field(
        default=False, description="The console's monitor: shown, never waited for."
    )


class ScreenSync(Model):
    error_ms: float | None = Field(default=None, description="p95 of picture vs timeline.")
    rtt_ms: float | None = None
    drift_ppm: float | None = None
    dropped_frames: Annotated[int, Field(ge=0)] = 0


class ScreenStatus(Model):
    state: ScreenState
    epoch: Annotated[int, Field(ge=0)] | None = Field(
        default=None, description="The session epoch this state is about."
    )
    ready: bool = Field(default=False, description="Its first frame is on screen, at the cue.")
    flags: list[ScreenFlag] = Field(default_factory=list)
    cache: list[ContentCache] = Field(default_factory=list)
    sync: ScreenSync = Field(default_factory=ScreenSync)
    error: str | None = None


class AudioDevice(Model):
    id: NonEmptyStr = Field(description="Stable across reboots.")
    name: str
    channels: Annotated[int, Field(ge=1)] = 2
    sample_rate: Annotated[int, Field(gt=0)] = 48000
    latency_ms: Annotated[float, Field(ge=0)] | None = None
    default: bool = False
    connected: bool = True
    bluetooth: bool = False


class AudioError(Model):
    """Something the audio engine could not do, until it can again."""

    code: Literal["output_failed", "output_lost", "load_failed", "master_lost"]
    device: str | None = Field(default=None, description="The audio device id.")
    item_id: str | None = None
    message: str


class AudioStatus(Model):
    """What `kp-audio` reports every second and on every change."""

    state: AudioState = "idle"
    epoch: Annotated[int, Field(ge=0)] | None = None
    ready: bool = Field(default=False, description="The cued song is decoded and primed.")
    item_id: str | None = None
    position: float | None = None
    errors: list[AudioError] = Field(default_factory=list)
    devices: list[AudioDevice] = Field(default_factory=list)
    cache: list[ContentCache] = Field(default_factory=list)
    sync: dict[str, float] = Field(
        default_factory=dict, description="Diagnostics: measured drift (ppm) and offsets (ms)."
    )
