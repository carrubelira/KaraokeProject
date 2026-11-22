"""Server settings (plan v4 §3): where the data lives, the port, TLS and the limits."""

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

GIB = 1024**3

REPO = Path(__file__).resolve().parents[4]


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def default_data_dir() -> Path:
    """`%LOCALAPPDATA%\\karaoke` on Windows, `$XDG_DATA_HOME/karaoke` elsewhere."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "karaoke"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "karaoke"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = "0.0.0.0"  # noqa: S104 - workers and players on the LAN and Tailscale reach it
    port: int = 8765
    # TLS on by default with a certificate of its own (nodes pin its fingerprint when they
    # enrol); off only for tests and a development server behind something that adds it.
    tls: bool = True
    # Extra names and addresses for the certificate (the machine's own are always in).
    tls_names: tuple[str, ...] = ()
    web_dir: Path | None = field(default_factory=lambda: REPO / "web" / "build")
    max_upload_bytes: int = 4 * GIB
    # The blob store may use this much; the oldest trash goes first when it is passed.
    quota_bytes: int | None = None
    trash_days: int = 30
    # A worker that has not renewed its lease in this long has lost the task.
    lease_seconds: float = 30.0
    # How long a worker's lease request waits for a task before answering "nothing".
    lease_wait_seconds: float = 20.0
    # A command reaches a player and its outputs this long after it is given, so every output
    # starts on the same instant.
    command_lead_seconds: float = 0.3
    enrollment_hours: float = 24.0

    @classmethod
    def from_env(cls, **overrides: Any) -> "Settings":
        env = os.environ
        values: dict[str, Any] = {
            "data_dir": Path(env["KARAOKE_DATA"]) if env.get("KARAOKE_DATA") else None,
            "port": int(env.get("KARAOKE_PORT") or 8765),
        }
        if env.get("KARAOKE_NO_TLS") is not None:
            values["tls"] = not _flag(env.get("KARAOKE_NO_TLS"))
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
    def tls_dir(self) -> Path:
        return self.data_dir / "tls"

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
        for path in (self.blobs_dir, self.uploads_dir, self.tls_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)
