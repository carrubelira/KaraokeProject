"""Contracts v2: a song as a manifest of independent tracks stored by content (plan v4 §5).

A manifest names its tracks by the SHA-256 of their bytes, so a player or a worker downloads a
blob once, checks it, and only fetches what changed when a new version of the song is made.
Every track shares one timeline: t = 0 is the start of the song, and each track says where it
starts (`offset`) and how long it lasts.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from karaoke_contracts.doc import HexColor, LanguageFallback, Line, NonEmptyStr

MANIFEST_SCHEMA_VERSION = "2.0.0"

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Language = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")]
ContentId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]
Seconds = Annotated[float, Field(ge=0)]
_SLUG = re.compile(r"[^a-z0-9]+")


class Model(BaseModel):
    """Strict: v2 has no older readers to keep happy, so unknown fields are an error."""

    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        json_schema_serialization_defaults_required=True,
    )


class Blob(Model):
    sha256: Sha256
    size: Annotated[int, Field(ge=0)]
    media_type: NonEmptyStr


class AudioInfo(Model):
    codec: Literal["opus"] = "opus"
    container: Literal["ogg"] = "ogg"
    sample_rate: Literal[48000] = 48000
    channels: Annotated[int, Field(ge=1, le=2)] = 2
    preskip: Annotated[int, Field(ge=0, description="Opus pre-skip, in 48 kHz samples.")]
    gain_db: float = Field(
        default=0.0,
        description="Gain the player applies to bring the song to -14 LUFS without clipping; "
        "the same for every audio track, so guide vocals and music keep their balance.",
    )
    loudness_lufs: float | None = Field(
        default=None, description="Integrated loudness of the mix once `gain_db` is applied."
    )


class VideoInfo(Model):
    codec: Literal["h264", "hevc", "av1"]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    fps: Annotated[float, Field(gt=0)]


class Track(Model):
    kind: Literal["vocals", "instrumental", "video", "lyrics", "cover"]
    blob: Blob
    offset: float = Field(default=0.0, description="Song time of the track's first sample.")
    duration: Seconds | None = None
    audio: AudioInfo | None = None
    video: VideoInfo | None = None

    @model_validator(mode="after")
    def _info_matches_kind(self) -> "Track":
        if (self.kind in ("vocals", "instrumental")) != (self.audio is not None):
            raise ValueError("audio tracks, and only they, carry `audio`")
        if (self.kind == "video") != (self.video is not None):
            raise ValueError("video tracks, and only they, carry `video`")
        return self


class Manifest(Model):
    schema_version: Annotated[str, StringConstraints(pattern=r"^2\.\d+\.\d+$")] = (
        MANIFEST_SCHEMA_VERSION
    )
    content_id: ContentId
    version: Annotated[int, Field(ge=1)] = 1
    parent: Sha256 | None = Field(default=None, description="Hash of the previous version.")
    created_at: datetime
    title: NonEmptyStr
    artist: str | None = None
    language: Language
    duration: Annotated[float, Field(gt=0)]
    tracks: Annotated[list[Track], Field(min_length=1)]

    @model_validator(mode="after")
    def _one_of_each_audio_and_lyrics(self) -> "Manifest":
        kinds = [t.kind for t in self.tracks]
        for kind in ("vocals", "instrumental", "lyrics", "cover"):
            if kinds.count(kind) > 1:
                raise ValueError(f"more than one {kind} track")
        if "instrumental" not in kinds:
            raise ValueError("a manifest needs an instrumental track")
        if "lyrics" not in kinds:
            raise ValueError("a manifest needs a lyrics track")
        videos = [(t.video.width, t.video.height, t.video.codec) for t in self.tracks if t.video]
        if len(videos) != len(set(videos)):
            raise ValueError("two video tracks with the same size and codec")
        return self

    def track(self, kind: str) -> Track | None:
        return next((t for t in self.tracks if t.kind == kind), None)

    def blobs(self) -> list[Blob]:
        return [t.blob for t in self.tracks]


class Singer(Model):
    id: NonEmptyStr
    name: str | None = None
    color: HexColor | None = None


class LyricsProvenance(Model):
    lyrics_source: Literal["user", "asr", "lrclib"]
    separation_model: str | None = None
    asr_model: str | None = None
    align_model: str | None = None
    engine_version: NonEmptyStr
    language_fallbacks: list[LanguageFallback] = Field(default_factory=list)


class Lyrics(Model):
    """The `lyrics` track: lines, words and syllables with times and confidence, nothing else."""

    schema_version: Annotated[str, StringConstraints(pattern=r"^2\.\d+\.\d+$")] = (
        MANIFEST_SCHEMA_VERSION
    )
    language: Language
    singers: list[Singer] = Field(default_factory=list)
    lines: list[Line]
    provenance: LyricsProvenance
    edited: bool = False


def slug(text: str) -> str:
    """A content id from a title: lower case ASCII letters, digits and dashes."""
    import unicodedata

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _SLUG.sub("-", ascii_text.lower()).strip("-")[:80] or "song"


def canonical_json(model: BaseModel) -> bytes:
    """The bytes a manifest or lyrics track is stored as: sorted keys, no spaces, UTF-8.

    Line, Word and Part allow extra fields (contracts v1); they are kept as they come.
    """
    return json.dumps(
        model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate_json(path.read_bytes())
