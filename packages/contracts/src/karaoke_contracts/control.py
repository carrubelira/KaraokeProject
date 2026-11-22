"""Contracts v2: the queue, and how the backend's audio is routed and calibrated (decision 011)."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from karaoke_contracts.doc import NonEmptyStr
from karaoke_contracts.manifest import ContentId, Model, Sha256

OutputPolicy = Literal["pause", "continue"]


class Anchor(Model):
    """A song position that holds at an instant (µs on the server's monotonic clock) and moves
    at a rate (0 paused, 1 playing)."""

    position: float
    instant: int
    rate: Annotated[float, Field(ge=0)] = 1.0


class QueueItem(Model):
    id: NonEmptyStr
    content_id: ContentId
    manifest: Sha256 | None = Field(default=None, description="Pinned version; None = latest.")
    start: Annotated[float, Field(ge=0)] | None = Field(default=None, description="Entry point.")
    end: Annotated[float, Field(gt=0)] | None = Field(default=None, description="Exit point.")
    semitones: Annotated[float, Field(ge=-12, le=12)] = 0.0
    singer: str | None = None

    @model_validator(mode="after")
    def _start_before_end(self) -> "QueueItem":
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("the entry point must come before the exit point")
        return self


class Queue(Model):
    """What the stage will play, in order: one per backend, with an optimistic version."""

    version: Annotated[int, Field(ge=0)] = 0
    items: list[QueueItem] = Field(default_factory=list)


class Route(Model):
    track: Literal["vocals", "instrumental"]
    output: NonEmptyStr = Field(description="An audio device id.")
    gain_db: float | None = Field(default=0.0, description="None mutes the route.")
    delay_ms: Annotated[float, Field(ge=0, le=2000)] = 0.0


class Routing(Model):
    master: str | None = Field(default=None, description="Audio device whose clock rules.")
    routes: list[Route] = Field(default_factory=list)
    policies: dict[str, OutputPolicy] = Field(
        default_factory=dict,
        description="What happens when an output disappears; default: pause if it is the "
        "master, continue otherwise.",
    )


class AudioConfig(Model):
    """How `kp-audio` sends the stems to the backend's sound cards."""

    routing: Routing = Field(default_factory=Routing)
    calibration_ms: dict[str, float] = Field(
        default_factory=dict,
        description="Per stable device id: how late it really is, beyond what the OS reports.",
    )
