"""End to end, on one machine (`make e2e-v4`): the server, a worker with the fake engine and
kp-audio with two simulated outputs (decision 011).

A song is uploaded, analysed and reviewed, made by the worker and put in the queue. The
operator cues it: kp-audio decodes it and says it is ready, and the session is `cued`. Nothing
sounds until the operator starts it; then both outputs play it in sync (the guide vocals only
on the second), it is transposed and paused. Run with `uv run python audio/tests/e2e.py` after
`cargo build -p kp-audio`.
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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
EXE = ".exe" if os.name == "nt" else ""
AUDIO = REPO / "audio" / "target" / "debug" / f"kp-audio{EXE}"
TOKEN = "e2e-audio-secret"  # noqa: S105 - a test server's own secret


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Api:
    def __init__(self, base: str, token: str) -> None:
        self.base, self.token = base, token

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        headers: dict[str, str] | None = None,
        raw: bytes | None = None,
    ) -> Any:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        with urllib.request.urlopen(request, timeout=30) as answer:
            text = answer.read()
            return json.loads(text) if text else None

    def order(self, command: str, **body: Any) -> Any:
        return self.call("POST", "/api/stage/commands", {"command": command, **body})


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
    if not AUDIO.is_file():
        print(f"build kp-audio first: {AUDIO} is missing", file=sys.stderr)
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="kp-e2e-"))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server_data, worker_data = tmp / "server", tmp / "worker"
    procs: list[subprocess.Popen[bytes]] = []
    env = {**os.environ, "KARAOKE_FAKE_STAGE_SECONDS": "0.01", "KARAOKE_AUDIO_TOKEN": TOKEN}
    try:
        token = cli("karaoke-server", "--data", str(server_data), "operator", "add", "e2e")
        server_log = (tmp / "server.log").open("wb")
        procs.append(
            subprocess.Popen(
                [
                    "karaoke-server",
                    "--data",
                    str(server_data),
                    "serve",
                    "--audio",
                    "external",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--web",
                    str(tmp / "noweb"),
                ],
                env=env,
                stdout=server_log,
                stderr=server_log,
            )
        )
        api = Api(base, token)
        wait("the server", lambda: _alive(base))
        worker_token = api.call("POST", "/api/enrollments", {"kind": "worker"})["token"]
        cli("karaoke-worker", "--data", str(worker_data), "enroll", base, worker_token)
        procs.append(
            subprocess.Popen(
                ["karaoke-worker", "--data", str(worker_data), "run", "--fake"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        audio_log = (tmp / "audio.log").open("wb")
        procs.append(
            subprocess.Popen(
                [
                    str(AUDIO),
                    "run",
                    "--server",
                    base,
                    "--store",
                    str(server_data / "blobs"),
                    "--virtual-outputs",
                    "2",
                    "--diagnose",
                ],
                env=env,
                stdout=audio_log,
                stderr=audio_log,
            )
        )
        stage = lambda: api.call("GET", "/api/stage")  # noqa: E731
        wait("kp-audio", lambda: stage()["audio"]["online"])

        song = b"ID3" + bytes(2000)
        upload = api.call("POST", "/api/uploads", {"filename": "Proba.mp3", "size": len(song)})
        api.call("PATCH", f"/api/uploads/{upload['id']}", raw=song, headers={"Upload-Offset": "0"})
        job = api.call(
            "POST", "/api/jobs", {"upload": upload["id"], "lyrics": "la la", "title": "Proba"}
        )
        wait(
            "the analysis",
            lambda: api.call("GET", f"/api/jobs/{job['id']}")["state"] == "review" or None,
        )
        review = {"title": "Proba", "language": "gl", "lyrics": "la la", "add_to_queue": True}
        api.call("POST", f"/api/jobs/{job['id']}/confirm", review)
        wait("the worker to make the song", lambda: _job_done(api, job["id"]), 120)
        queue = wait("the song in the queue", lambda: api.call("GET", "/api/stage/queue")["items"])
        print(f"queued {queue[0]['content_id']}")

        config = {
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
                "policies": {},
            },
            "calibration_ms": {},
        }
        api.call("PUT", "/api/stage/audio", config)
        cued = api.order("cue")
        assert cued["state"] == "cueing", cued
        wait("kp-audio to have the song ready", lambda: stage()["session"]["state"] == "cued")
        status = lambda: stage()["audio"]["status"]  # noqa: E731
        assert status()["ready"]
        assert status()["epoch"] == cued["epoch"]
        # The demo sings from 4 s: start just before, so both outputs make sound.
        api.order("seek", position=3.8)
        time.sleep(1.5)
        held = status()["position"]
        assert abs(held - 3.8) < 0.01, f"nothing sounds before the operator's start ({held})"
        started = api.order("start")
        assert started["state"] == "playing"
        wait("playback", lambda: status()["state"] == "playing")
        first = status()["position"]
        time.sleep(3)
        now = status()
        moved = now["position"] - first
        print(f"position {first:.2f} -> {now['position']:.2f}; sync {json.dumps(now['sync'])}")
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
        api.order("pitch", value=-2)
        wait("the new key", lambda: stage()["session"]["semitones"] == -2)
        api.order("pause")
        wait("pause", lambda: status()["state"] == "paused")
        held = status()["position"]
        time.sleep(1.5)
        assert abs(status()["position"] - held) < 0.01, "paused means paused"
    except (AssertionError, urllib.error.URLError):
        for name in ("server.log", "audio.log"):
            print(f"--- {name}", file=sys.stderr)
            print((tmp / name).read_text(errors="replace")[-4000:], file=sys.stderr)
        raise
    else:
        print("e2e: ok")
        return 0
    finally:
        for proc in reversed(procs):
            # Windows has no SIGINT for a child (CTRL_BREAK would reach this process too).
            if os.name == "nt":
                proc.terminate()
            else:
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
        with urllib.request.urlopen(base + "/api/server", timeout=2):
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
