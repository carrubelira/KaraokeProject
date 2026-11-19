"""End to end, on one machine (`make e2e-v4`): the v4 server, a worker with the fake engine and
the native player headless with two simulated outputs.

A song is uploaded, made by the worker, put on a playlist; the player downloads it, loads it,
plays it on both outputs (the guide vocals only on the second) in sync, transposes it and
pauses. Run with `uv run python player/tests/e2e.py` after `cargo build -p kp-player`.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PLAYER = REPO / "player" / "target" / "debug" / "kp-player"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Api:
    def __init__(self, base: str, token: str) -> None:
        self.base, self.token = base, token

    def call(self, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None,
             raw: bytes | None = None) -> Any:  # fmt: skip
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        with urllib.request.urlopen(request, timeout=30) as answer:  # noqa: S310 - local server
            text = answer.read()
            return json.loads(text) if text else None


def wait(what: str, check: Any, seconds: float = 60) -> Any:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {what}")


def cli(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    if not PLAYER.is_file():
        print(f"build the player first: {PLAYER} is missing", file=sys.stderr)
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="kp-e2e-"))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server_data, worker_data, player_data = tmp / "server", tmp / "worker", tmp / "player"
    procs: list[subprocess.Popen[bytes]] = []
    env = {**os.environ, "KARAOKE_FAKE_STAGE_SECONDS": "0.01"}
    try:
        token = cli("karaoke-server", "--data", str(server_data), "operator", "add", "e2e")
        procs.append(subprocess.Popen(
            ["karaoke-server", "--data", str(server_data), "serve", "--no-tls", "--host", "127.0.0.1",
             "--port", str(port), "--web", str(tmp / "noweb")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))  # fmt: skip
        api = Api(base, token)
        wait("the server", lambda: _alive(base))
        worker_token = api.call("POST", "/api/enrollments", {"kind": "worker"})["token"]
        cli("karaoke-worker", "--data", str(worker_data), "enroll", base, worker_token)
        procs.append(subprocess.Popen(["karaoke-worker", "--data", str(worker_data), "run", "--fake"], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))  # fmt: skip

        song = b"ID3" + bytes(2000)
        upload = api.call("POST", "/api/uploads", {"filename": "Proba.mp3", "size": len(song)})
        api.call("PATCH", f"/api/uploads/{upload['id']}", raw=song, headers={"Upload-Offset": "0"})
        job = api.call(
            "POST", "/api/jobs", {"upload": upload["id"], "lyrics": "la la", "title": "Proba"}
        )
        done = wait("the worker to make the song", lambda: _job_done(api, job["id"]), 120)
        content = done["result"]["content_id"]
        print(f"made {content}")

        player_token = api.call("POST", "/api/enrollments", {"kind": "player"})["token"]
        print(
            cli(
                str(PLAYER),
                "--data",
                str(player_data),
                "enroll",
                base,
                player_token,
                "--name",
                "sala",
            )
        )
        player_log = (tmp / "player.log").open("wb")
        procs.append(subprocess.Popen(
            [str(PLAYER), "--data", str(player_data), "run", "--headless", "--virtual-outputs", "2", "--diagnose"],
            stdout=player_log, stderr=player_log))  # fmt: skip
        player = wait(
            "the player",
            lambda: next((p for p in api.call("GET", "/api/players") if p["online"]), None),
        )
        playlist = api.call("POST", "/api/playlists", {"name": "Noite"})
        playlist["items"] = [{"id": "one", "content_id": content, "manifest": None, "start": None, "end": None,
                              "semitones": 0, "singer": "Uxía"}]  # fmt: skip
        api.call("PUT", f"/api/playlists/{playlist['id']}", playlist)
        config = {
            "playlist_id": playlist["id"],
            "routing": {
                "master": "virtual:main",
                "routes": [
                    {
                        "track": "instrumental",
                        "output": "virtual:main",
                        "gain_db": 0,
                        "delay_ms": 0,
                    },
                    {"track": "vocals", "output": "virtual:main", "gain_db": -6, "delay_ms": 0},
                    {"track": "vocals", "output": "virtual:out1", "gain_db": 0, "delay_ms": 0},
                ],
                "screens": [],
                "policies": {},
            },
            "calibration": {"audio_ms": {}, "display_ms": {}},
        }
        api.call("PUT", f"/api/players/{player['id']}/config", config)
        status = lambda: api.call("GET", "/api/players")[0]["status"]  # noqa: E731
        wait(
            "the song in the player's cache",
            lambda: any(c["state"] == "ready" for c in status()["cache"]),
        )
        api.call(
            "POST", f"/api/players/{player['id']}/commands", {"command": "load", "item_id": "one"}
        )
        wait("the song loaded", lambda: status()["state"] == "paused")
        # The demo sings from 4 s: start just before, so both outputs make sound.
        api.call(
            "POST", f"/api/players/{player['id']}/commands", {"command": "play", "position": 3.8}
        )
        wait("playback", lambda: status()["state"] == "playing")
        first = status()["position"]
        time.sleep(3)
        now = status()
        moved = now["position"] - first
        print(f"position {first:.2f} → {now['position']:.2f}; sync {json.dumps(now['sync'])}")
        assert 2.0 < moved < 4.5, moved
        sync = now["sync"]
        assert sync["virtual:main.rms"] > 0.001, "the main output plays"
        assert sync["virtual:out1.rms"] > 0.001, "the second output plays the guide vocals"
        assert abs(sync["virtual:out1.correction_ppm"] - 60) < 30, (
            "the second output absorbs its drift"
        )
        assert abs(sync.get("virtual:main.offset_ms", 0)) < 5, (
            "the heard sound is where the timeline says"
        )
        assert sync["virtual:out1.jumps"] <= 1
        api.call("POST", f"/api/players/{player['id']}/commands", {"command": "pitch", "value": -2})
        wait("the new key", lambda: status()["semitones"] == -2)
        api.call("POST", f"/api/players/{player['id']}/commands", {"command": "pause"})
        wait("pause", lambda: status()["state"] == "paused")
        held = status()["position"]
        time.sleep(1.5)
        assert abs(status()["position"] - held) < 0.01, "paused means paused"
        print("e2e: ok")
        return 0
    finally:
        for proc in reversed(procs):
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if os.environ.get("KP_E2E_KEEP"):
            print(f"kept {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def _alive(base: str) -> bool:
    try:
        with urllib.request.urlopen(base + "/api/server", timeout=2):  # noqa: S310 - local server
            return True
    except OSError:
        return False


def _job_done(api: Api, job_id: str) -> Any:
    job = api.call("GET", f"/api/jobs/{job_id}")
    if job["state"] == "failed":
        raise AssertionError(f"the job failed: {job}")
    return job if job["state"] == "done" else None


if __name__ == "__main__":
    raise SystemExit(main())
