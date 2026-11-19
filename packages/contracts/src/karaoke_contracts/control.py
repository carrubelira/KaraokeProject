"""Contracts v2: playlists, player orders, routing and calibration (plan v4 §6 and §7)."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from karaoke_contracts.doc import NonEmptyStr
from karaoke_contracts.manifest import ContentId, Model, Sha256

OutputPolicy = Literal["pause", "continue"]


class Anchor(Model):
    """A song position that holds at an instant (µs on the server's clock) and moves at a rate."""

    position: float
    instant: int
    rate: Annotated[float, Field(ge=0)] = 1.0


class PlaylistItem(Model):
    id: NonEmptyStr
    content_id: ContentId
    manifest: Sha256 | None = Field(default=None, description="Pinned version; None = latest.")
    start: Annotated[float, Field(ge=0)] | None = Field(default=None, description="Entry point.")
    end: Annotated[float, Field(gt=0)] | None = Field(default=None, description="Exit point.")
    semitones: Annotated[float, Field(ge=-12, le=12)] = 0.0
    singer: str | None = None

    @model_validator(mode="after")
    def _start_before_end(self) -> "PlaylistItem":
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("the entry point must come before the exit point")
        return self


class Playlist(Model):
    id: NonEmptyStr
    name: NonEmptyStr
    version: Annotated[int, Field(ge=0)] = 0
    items: list[PlaylistItem] = Field(default_factory=list)
    player_id: str | None = None


Command = Literal[
    "load", "play", "pause", "seek", "next", "previous", "stop", "volume", "pitch", "reload"
]


class PlayerCommand(Model):
    id: NonEmptyStr
    command: Command
    item_id: str | None = None
    anchor: Anchor | None = Field(default=None, description="Where and when, for play/seek.")
    value: float | None = Field(default=None, description="Volume (0 to 2) or semitones.")
    issued_at: int = Field(description="µs on the server's clock.")


class Route(Model):
    track: Literal["vocals", "instrumental"]
    output: NonEmptyStr = Field(description="An audio device id.")
    gain_db: float | None = Field(default=0.0, description="None mutes the route.")
    delay_ms: Annotated[float, Field(ge=0, le=2000)] = 0.0


class Screen(Model):
    display: NonEmptyStr
    layout: Literal["video-lyrics", "lyrics", "video", "off"] = "video-lyrics"
    theme: str = "clasico"


class Routing(Model):
    master: str | None = Field(default=None, description="Audio device whose clock rules.")
    routes: list[Route] = Field(default_factory=list)
    screens: list[Screen] = Field(default_factory=list)
    policies: dict[str, OutputPolicy] = Field(
        default_factory=dict,
        description="What happens when an output disappears; default: pause if it is the "
        "master, continue otherwise.",
    )


class Calibration(Model):
    """Per stable device id: how late it really is, beyond what the OS reports."""

    audio_ms: dict[str, float] = Field(default_factory=dict)
    display_ms: dict[str, float] = Field(default_factory=dict)


class PlayerConfig(Model):
    routing: Routing = Field(default_factory=Routing)
    calibration: Calibration = Field(default_factory=Calibration)
    playlist_id: str | None = None
