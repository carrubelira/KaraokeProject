"""The worker's own settings and identity, kept in `worker.json` in its data folder."""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def default_data_dir() -> Path:
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "karaoke-worker"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "karaoke-worker"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "karaoke-worker"


@dataclass
class WorkerConfig:
    server: str
    node_id: str
    credential: str
    name: str
    # Task kinds it takes; "fetch" needs yt-dlp and the internet.
    tasks: list[str] = field(default_factory=lambda: ["fetch", "analyze", "make", "render"])
    internet: bool = True
    # It runs on the server's machine: it reads the server's blobs from disk, and the server gives
    # it no GPU work while a song plays there.
    same_host: bool = False
    # Blob cache it keeps for affinity (inputs of the next task are often already here).
    cache_bytes: int = 20 * 1024**3
    fake_engine: bool = False
    # AcoustID application key, to recognise songs by their sound (KARAOKE_ACOUSTID_KEY wins).
    acoustid_key: str | None = None

    @classmethod
    def load(cls, data_dir: Path) -> "WorkerConfig":
        path = data_dir / "worker.json"
        if not path.is_file():
            raise FileNotFoundError(f"{path}: enrol first (karaoke-worker enroll)")
        data = json.loads(path.read_text(encoding="utf-8"))
        # Settings of before decision 011: no TLS (the server is plain HTTP on the LAN) and no
        # player's lock file.
        for gone in ("fingerprint", "player_lock"):
            data.pop(gone, None)
        server = str(data.get("server", ""))
        if server.startswith("https://"):
            data["server"] = "http://" + server[len("https://") :]
        return cls(**data)

    def save(self, data_dir: Path) -> Path:
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "worker.json"
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        if os.name != "nt":
            path.chmod(0o600)
        return path
