"""Starts the karaoke on this machine: the server (with kp-audio, its sound) and a worker.

    scripts/start.ps1            Windows
    scripts/start.sh             Linux (or `make start`)

It does what is missing first, and only that: the Python environment (with the GPU stack when
there is an NVIDIA GPU), the web app's build, kp-audio's build, an operator for the console and
the enrolment of a worker on this machine. Then it runs the server and the worker in this window,
their lines prefixed, starts again whatever stops on its own, and stops everything on Ctrl+C.

The worker runs here on Linux. On Windows it runs inside WSL when WSL has the project's
environment (the engine is not supported on native Windows, see NOTICE.md): the server and
kp-audio stay on Windows, next to the sound cards, and the worker reaches them through WSL's
gateway (scripts/wsl-worker.sh).

Options: --worker auto|here|wsl|none (--no-worker: none), --no-audio (no sound: screens only),
--fake (a worker that pretends, to try the system without a GPU), --port, --data, --setup
(prepare and exit). It needs only Python's standard library, so it runs before the environment
exists.
"""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"
EXE = ".exe" if WINDOWS else ""
# Windows and WSL may share this checkout: each keeps its own environment.
DEFAULT_ENV = REPO / (".venv-windows" if WINDOWS else ".venv")
RESTART_SECONDS = 5


def say(text: str) -> None:
    print(f"> {text}", flush=True)


def warn(text: str) -> None:
    print(f"! {text}", flush=True)


def newest(paths: Iterable[Path]) -> float:
    """The latest change among files (recursively for folders); 0 if there are none."""
    latest = 0.0
    for path in paths:
        if path.is_file():
            latest = max(latest, path.stat().st_mtime)
        elif path.is_dir():
            for child in path.rglob("*"):
                if (
                    child.is_file()
                    and "node_modules" not in child.parts
                    and "target" not in child.parts
                ):
                    latest = max(latest, child.stat().st_mtime)
    return latest


def run(cmd: Sequence[str | Path], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(c) for c in cmd], text=True, check=False, **kwargs)  # type: ignore[call-overload]


class Machine:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.env_dir = Path(os.environ.get("UV_PROJECT_ENVIRONMENT") or DEFAULT_ENV)
        self.env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(self.env_dir)}
        if args.data:
            self.env["KARAOKE_DATA"] = str(Path(args.data).resolve())
        bin_dir = self.env_dir / ("Scripts" if WINDOWS else "bin")
        self.python = bin_dir / f"python{EXE}"
        self.server_bin = bin_dir / f"karaoke-server{EXE}"
        self.worker_bin = bin_dir / f"karaoke-worker{EXE}"
        self.gpu = (
            shutil.which("nvidia-smi") is not None
            and run(["nvidia-smi", "-L"], capture_output=True).returncode == 0
        )
        self.worker = self._worker_place()

    # Where the worker runs

    def wsl(self, script: str) -> subprocess.CompletedProcess[str]:
        """Runs a bash line in WSL's default distribution, in this repository."""
        return run(
            ["wsl.exe", "--", "bash", "-lc", f"cd '{self.wsl_repo}' && {script}"],
            capture_output=True,
        )

    @property
    def wsl_repo(self) -> str:
        drive, rest = str(REPO).split(":", 1)
        return f"/mnt/{drive.lower()}{rest.replace(chr(92), '/')}"

    def _worker_place(self) -> str:
        wanted = "none" if self.args.no_worker else self.args.worker
        if wanted != "auto":
            return wanted
        if not WINDOWS or self.args.fake:
            return "here"
        ready = (
            shutil.which("wsl.exe") and self.wsl("test -x .venv/bin/karaoke-worker").returncode == 0
        )
        if ready:
            return "wsl"
        warn(
            "No worker environment in WSL (run scripts/install.sh there): the worker here pretends."
        )
        return "here"

    # Preparing

    def environment(self) -> None:
        if not shutil.which("uv"):
            sys.exit("uv is missing: https://docs.astral.sh/uv/ (winget install astral-sh.uv)")
        # The GPU stack only where the worker really makes karaokes (on Linux; WSL has its own).
        here = self.worker == "here" and not WINDOWS and not self.args.fake
        extra = ["--extra", "ml"] if self.gpu and here else []
        say(f"Python environment in {self.env_dir}" + (" with the GPU stack" if extra else ""))
        # --inexact keeps what is installed beyond the lock (the GPU stack, libclang).
        if run(["uv", "sync", "--inexact", *extra], cwd=REPO, env=self.env).returncode:
            sys.exit("uv sync failed")

    def web(self) -> None:
        index = REPO / "web" / "build" / "index.html"
        sources = [REPO / "web" / p for p in ("src", "static", "package.json", "vite.config.ts")]
        if index.is_file() and index.stat().st_mtime >= newest(sources):
            return
        say("Building the web app")
        pnpm = shutil.which("pnpm")
        if pnpm and run([pnpm, "--dir", "web", "build"], cwd=REPO).returncode == 0:
            return
        if index.is_file():
            warn("The web app could not be built: serving the build there is (it may be old).")
        else:
            warn("The web app is not built: run `pnpm --dir web install && pnpm --dir web build`.")
        if WINDOWS:
            warn("If web/node_modules was installed from WSL, build it there.")

    def kp_audio(self) -> Path | None:
        """kp-audio, built if it is missing or older than its sources; None: no sound."""
        if self.args.no_audio:
            return None
        exe = REPO / "audio" / "target" / "release" / f"kp-audio{EXE}"
        sources = [
            REPO / "audio" / "crates",
            REPO / "audio" / "Cargo.toml",
            REPO / "audio" / "Cargo.lock",
        ]
        if exe.is_file() and exe.stat().st_mtime >= newest(sources):
            return exe
        cargo = shutil.which("cargo")
        if not cargo:
            warn("Rust (cargo) is missing: there will be no sound. https://rustup.rs")
            return exe if exe.is_file() else None
        say("Building kp-audio (the first time takes a few minutes)")
        env = dict(self.env)
        features: list[str] = []
        if WINDOWS:
            env.update(self._windows_build_tools())
            if "LIBCLANG_PATH" not in env:
                warn("No libclang: kp-audio is built without the key change.")
                features = ["--no-default-features", "--features", "native"]
        built = run(
            [cargo, "build", "--release", "-p", "kp-audio", *features], cwd=REPO / "audio", env=env
        )
        if built.returncode:
            warn("kp-audio did not build: there will be no sound.")
            return exe if exe.is_file() else None
        return exe

    def _windows_build_tools(self) -> dict[str, str]:
        """cmake (for libopus) and libclang (for the key change) from what this machine has."""
        found: dict[str, str] = {}
        tools = (
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
            / "Microsoft Visual Studio"
        )
        if not shutil.which("cmake") and "CMAKE" not in os.environ:
            for cmake in tools.glob(
                "*/*/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe"
            ):
                found["CMAKE"] = str(cmake)
                break
        if "LIBCLANG_PATH" not in os.environ:
            places = [
                *tools.glob("*/*/VC/Tools/Llvm/x64/bin"),
                Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "LLVM" / "bin",
                self.env_dir / "Lib" / "site-packages" / "clang" / "native",
            ]
            dll = next((p for p in places if (p / "libclang.dll").is_file()), None)
            if dll is None:
                # The libclang wheel brings the DLL: no system install needed.
                say("Getting libclang (for the key change) into the environment")
                run(
                    ["uv", "pip", "install", "--python", self.python, "libclang"],
                    cwd=REPO,
                    env=self.env,
                )
                native = self.env_dir / "Lib" / "site-packages" / "clang" / "native"
                dll = native if (native / "libclang.dll").is_file() else None
            if dll is not None:
                found["LIBCLANG_PATH"] = str(dll)
        return found

    def operator(self) -> None:
        listed = run([self.server_bin, "operator", "list"], capture_output=True, env=self.env)
        if listed.stdout.strip():
            return
        made = run(
            [self.server_bin, "operator", "add", "Operador"], capture_output=True, env=self.env
        )
        token = made.stdout.strip()
        print(f"\n  The console's operator token (keep it): {token}\n", flush=True)

    def enrol_worker(self, base: str) -> None:
        """A worker on this machine, enrolled the first time (it then reads blobs from disk)."""
        config = self.worker_data / "worker.json"
        if config.is_file():
            # Enrolled before the worker kept it: one talking to this machine is on it.
            data = json.loads(config.read_text(encoding="utf-8"))
            host = urllib.parse.urlsplit(str(data.get("server", ""))).hostname
            if host in ("localhost", "127.0.0.1") and not data.get("same_host"):
                data["same_host"] = True
                config.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return
        say("Enrolling this machine as a worker")
        token = run([self.server_bin, "enroll"], capture_output=True, env=self.env).stdout.split()
        if not token:
            warn("Could not make an enrolment token")
            return
        name = socket.gethostname()
        enrolled = run(
            [self.worker_bin, "enroll", base, token[0], "--same-host", "--name", name], env=self.env
        )
        if enrolled.returncode:
            warn("The worker could not be enrolled")

    @property
    def worker_data(self) -> Path:
        if WINDOWS and os.environ.get("LOCALAPPDATA"):
            return Path(os.environ["LOCALAPPDATA"]) / "karaoke-worker"
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(base) / "karaoke-worker"


class Service:
    """A process kept running: its lines go to this window, prefixed; it starts again if it
    stops on its own."""

    def __init__(
        self, name: str, cmd: Sequence[str | Path], env: dict[str, str], *, hold_stdin: bool = False
    ) -> None:
        self.name, self.cmd, self.env = name, [str(c) for c in cmd], env
        # A process that stops when its stdin closes (the worker in WSL): ours stays open.
        self.hold_stdin = hold_stdin
        self.process: subprocess.Popen[str] | None = None
        self.stopping = False

    def start(self) -> None:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0  # Ctrl+C is ours to pass on
        self.process = subprocess.Popen(
            self.cmd,
            cwd=REPO,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if self.hold_stdin else subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            start_new_session=not WINDOWS,
        )
        threading.Thread(target=self._pump, args=(self.process,), daemon=True).start()

    def _pump(self, process: subprocess.Popen[str]) -> None:
        assert process.stdout is not None
        for line in process.stdout:
            print(f"[{self.name}] {line.rstrip()}", flush=True)

    def check(self) -> None:
        if self.stopping or self.process is None or self.process.poll() is None:
            return
        warn(f"{self.name} stopped (exit {self.process.returncode}); again in {RESTART_SECONDS} s")
        time.sleep(RESTART_SECONDS)
        if not self.stopping:
            self.start()

    def stop(self) -> None:
        self.stopping = True
        process = self.process
        if process is None or process.poll() is not None:
            return
        # A gentle stop first, so the server closes kp-audio and the worker hands its task back.
        if process.stdin is not None:
            process.stdin.close()
        if WINDOWS:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()


WORKER_PLACES = {
    "none": "",
    "here": " · a worker on this machine",
    "wsl": " · a worker in WSL (the GPU)",
}


def lan_address() -> str:
    """This machine's address on the LAN (nothing is sent: a UDP socket only picks a route)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 9))
            return str(probe.getsockname()[0])
        except OSError:
            return socket.gethostname()


def wait_for(url: str, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):  # noqa: S310 - this machine
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="start", description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data", help="the server's data folder (default: per user)")
    parser.add_argument(
        "--worker",
        choices=["auto", "here", "wsl", "none"],
        default="auto",
        help="where the worker runs (auto: in WSL on Windows, here on Linux)",
    )
    parser.add_argument("--no-worker", action="store_true", help="the same as --worker none")
    parser.add_argument("--no-audio", action="store_true", help="no sound (screens only)")
    parser.add_argument("--fake", action="store_true", help="a worker that pretends (no GPU)")
    parser.add_argument("--setup", action="store_true", help="prepare everything and exit")
    args = parser.parse_args(argv)
    # The services' lines may hold characters the console's code page lacks (Windows).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    machine = Machine(args)
    machine.environment()
    machine.web()
    audio = machine.kp_audio()
    machine.operator()
    if args.setup:
        say("Ready. Start it with scripts/start (without --setup).")
        return 0

    base = f"http://127.0.0.1:{args.port}"
    server = Service(
        "server",
        [machine.server_bin, "serve", "--port", str(args.port), "--audio", str(audio or "off")],
        machine.env,
    )
    services = [server]
    server.start()
    if not wait_for(f"{base}/api/server", 60):
        server.stop()
        sys.exit("The server did not start: see its lines above.")
    if machine.worker == "wsl":
        token = ""
        if machine.wsl("test -f ~/.local/share/karaoke-worker/worker.json").returncode:
            say("Enrolling the worker in WSL")
            made = run([machine.server_bin, "enroll"], capture_output=True, env=machine.env)
            token = made.stdout.split()[0] if made.stdout.split() else ""
        line = f"exec scripts/wsl-worker.sh {args.port} {token}".rstrip()
        worker = Service(
            "worker",
            ["wsl.exe", "--", "bash", "-lc", f"cd '{machine.wsl_repo}' && {line}"],
            machine.env,
            hold_stdin=True,
        )
        worker.start()
        services.append(worker)
    elif machine.worker == "here":
        machine.enrol_worker(base)
        worker_cmd: list[str | Path] = [machine.worker_bin, "run"]
        if args.fake or not machine.gpu or WINDOWS:
            if not args.fake:
                warn("No engine here (no NVIDIA GPU, or native Windows): the worker pretends.")
            worker_cmd.append("--fake")
        worker = Service("worker", worker_cmd, machine.env)
        worker.start()
        services.append(worker)

    here = lan_address()
    print(
        f"\n  Console:  http://localhost:{args.port}\n"
        f"  Screens:  http://{here}:{args.port}/pantalla  (any browser on the LAN)\n"
        f"  Sound:    {'kp-audio' if audio else 'none'}"
        f"{WORKER_PLACES[machine.worker]}\n"
        "  Ctrl+C stops everything.\n",
        flush=True,
    )
    try:
        while True:
            time.sleep(1)
            for service in services:
                service.check()
    except KeyboardInterrupt:
        say("Stopping")
    finally:
        for service in reversed(services):
            service.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
