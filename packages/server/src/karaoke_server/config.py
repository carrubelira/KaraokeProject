"""Server settings (plan v4 §3, decision 011): where the data lives, the port, the audio engine
and the limits."""

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

GIB = 1024**3

REPO = Path(__file__).resolve().parents[4]


def default_data_dir() -> Path:
    """`%LOCALAPPDATA%\\karaoke` on Windows, `$XDG_DATA_HOME/karaoke` elsewhere."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "karaoke"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "karaoke"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = "0.0.0.0"  # noqa: S104 - workers, screens and consoles on the LAN reach it
    port: int = 8765
    # Plain HTTP: everything is on one LAN (decision 011).
    # The audio engine: "auto" (kp-audio on the PATH or next to Python), a path to it, or "off"
    # (no sound: the stage keeps time for the screens alone, for development and tests).
    audio: str = "auto"
    # The secret kp-audio connects with; made at every start unless given (a kp-audio started
    # by hand, in development).
    audio_token: str | None = None
    web_dir: Path | None = field(default_factory=lambda: REPO / "web" / "build")
    max_upload_bytes: int = 4 * GIB
    # The blob store may use this much; the oldest trash goes first when it is passed.
    quota_bytes: int | None = None
    trash_days: int = 30
    # A worker that has not renewed its lease in this long has lost the task.
    lease_seconds: float = 30.0
    # How long a worker's lease request waits for a task before answering "nothing".
    lease_wait_seconds: float = 20.0
    # A start or a pause takes effect this long after it is given (at least: more if a screen
    # answers slowly), so the audio and every screen change on the same instant.
    go_lead_seconds: float = 0.12
    # A seek while playing, this long: the screens look for the frame meanwhile.
    seek_lead_seconds: float = 0.4
    # Songs after the one on that screens and audio download and get ready ahead.
    upcoming: int = 3
    enrollment_hours: float = 24.0

    @classmethod
    def from_env(cls, **overrides: Any) -> "Settings":
        env = os.environ
        values: dict[str, Any] = {
            "data_dir": Path(env["KARAOKE_DATA"]) if env.get("KARAOKE_DATA") else None,
            "port": int(env.get("KARAOKE_PORT") or 8765),
        }
        if env.get("KARAOKE_AUDIO"):
            values["audio"] = env["KARAOKE_AUDIO"]
        if env.get("KARAOKE_AUDIO_TOKEN"):
            values["audio_token"] = env["KARAOKE_AUDIO_TOKEN"]
        if env.get("KARAOKE_QUOTA_GB"):
            values["quota_bytes"] = int(float(env["KARAOKE_QUOTA_GB"]) * GIB)
        values.update({k: v for k, v in overrides.items() if v is not None})
        if values["data_dir"] is None:
            values["data_dir"] = default_data_dir()
        known = {f.name for f in fields(cls)}
        unknown = set(values) - known
        if unknown:
            raise TypeError(f"unknown settings: {', '.join(sorted(unknown))}")
        return cls(**values)

    @property
    def blobs_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def db_path(self) -> Path:
        # A new file: a v3 database (karaoke.db) next to it is left alone.
        return self.data_dir / "karaoke-v4.db"

    def ensure_dirs(self) -> None:
        for path in (self.blobs_dir, self.uploads_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)
