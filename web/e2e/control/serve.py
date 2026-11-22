"""A v4 server with a fake worker and a screen for the browser tests (`pnpm test:e2e`,
project `control`).

It writes the operator token to e2e/control/.token, then runs until stopped.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PORT = int(os.environ.get("KARAOKE_E2E_PORT", "8799"))
HERE = Path(__file__).resolve().parent


def main() -> int:
    data = Path(tempfile.mkdtemp(prefix="kp-web-e2e-"))
    base = f"http://127.0.0.1:{PORT}"
    server_data, worker_data = data / "server", data / "worker"
    run = lambda *args: subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()  # noqa: E731
    token = run("karaoke-server", "--data", str(server_data), "operator", "add", "e2e")
    (HERE / ".token").write_text(token, encoding="utf-8")
    env = {**os.environ, "KARAOKE_FAKE_STAGE_SECONDS": "0.2"}
    server = subprocess.Popen(
        ["karaoke-server", "--data", str(server_data), "serve", "--no-tls", "--host", "127.0.0.1",
         "--port", str(PORT), "--web", str(data / "noweb")]
    )  # fmt: skip
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/server", timeout=1)  # noqa: S310 - local
            break
        except OSError:
            time.sleep(0.1)
    enrol = run("karaoke-server", "--data", str(server_data), "enroll", "worker")
    run("karaoke-worker", "--data", str(worker_data), "enroll", base, enrol, "--name", "gpu-1")
    worker = subprocess.Popen(["karaoke-worker", "--data", str(worker_data), "run", "--fake"], env=env)
    # A screen (never connected): its queue is what the tests fill.
    screen = run("karaoke-server", "--data", str(server_data), "enroll", "player")
    body = {"token": screen, "kind": "player", "name": "sala", "capabilities": {"os": "linux"}}
    request = urllib.request.Request(
        f"{base}/api/nodes/enroll",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(request, timeout=5)  # noqa: S310 - local
    stop = lambda *_: (_ for _ in ()).throw(KeyboardInterrupt)  # noqa: E731
    signal.signal(signal.SIGTERM, stop)
    try:
        while server.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (worker, server):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(data, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
