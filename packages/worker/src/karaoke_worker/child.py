"""Runs each task in a process of its own, with its memory capped (plan v4 §4).

The engine's models keep their memory until the process that loaded them ends. On Linux the
child runs in a systemd scope with MemoryMax (when systemd is there), so the kernel stops only
the task; on Windows it is put in a Job Object with a memory limit that also kills it when the
worker goes away. Cancelling stops the scope, the job object or the process group.
"""

import asyncio
import contextlib
import functools
import hashlib
import json
import logging
import os
import secrets
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_worker.types import Event, Outcome

WINDOWS = sys.platform == "win32"

logger = logging.getLogger(__name__)

GIB = 1024**3
KILL_AFTER = 5.0
# Exit status of a process killed with SIGKILL, which is how the kernel stops it for memory.
KILLED = () if WINDOWS else (-signal.SIGKILL, 128 + signal.SIGKILL)
# Exit status Windows gives a process its job object killed for memory (ERROR_NOT_ENOUGH_QUOTA).
JOB_MEMORY_EXIT = 1816


@dataclass(frozen=True)
class SpawnSettings:
    data_dir: Path
    # Memory cap for each task's process; None works it out from the machine's RAM.
    memory_max: int | None = None
    memory_swap_max: int | None = None

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"


@functools.cache
def scope_available() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        result = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", "true"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _runner(spec_path: Path) -> list[str]:
    return [sys.executable, "-m", "karaoke_worker.runner", str(spec_path)]


def total_memory() -> int:
    if WINDOWS:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                ("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                ("total_page", ctypes.c_ulonglong), ("free_page", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong), ("free_virtual", ctypes.c_ulonglong),
                ("free_extended", ctypes.c_ulonglong),
            ]  # fmt: skip

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # type: ignore[attr-defined]
        return int(status.total)
    if sys.platform == "darwin":
        out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, check=False)
        return int(out.stdout.strip() or 0)
    return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))


class _JobObject:
    """A Windows job object: a memory limit, and death of every process in it on close."""

    def __init__(self, memory: int) -> None:
        import win32job

        self.handle = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(
            self.handle, win32job.JobObjectExtendedLimitInformation
        )
        info["BasicLimitInformation"]["LimitFlags"] = (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
        )
        info["JobMemoryLimit"] = memory
        win32job.SetInformationJobObject(
            self.handle, win32job.JobObjectExtendedLimitInformation, info
        )

    def add(self, pid: int) -> None:
        import win32api
        import win32con
        import win32job

        process = win32api.OpenProcess(
            win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid
        )
        win32job.AssignProcessToJobObject(self.handle, process)

    def kill(self) -> None:
        import win32job

        with contextlib.suppress(Exception):
            win32job.TerminateJobObject(self.handle, 1)


class ProcessSpawner:
    def __init__(
        self, settings: SpawnSettings, command: Callable[[Path], list[str]] = _runner
    ) -> None:
        self.settings = settings
        self.command = command
        # Units carry the worker's mark: a worker stops what it left behind, never the tasks of
        # another worker on the same machine.
        mark = hashlib.sha256(str(settings.data_dir.resolve()).encode()).hexdigest()[:8]
        self.unit_prefix = f"karaoke-{mark}-"

    def unit_for(self, job_id: str) -> str:
        # Unique per run: systemd keeps a unit's name for a moment after it ends.
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in job_id)
        return f"{self.unit_prefix}{safe}-{secrets.token_hex(3)}"

    def leftovers_pattern(self) -> str:
        return f"{self.unit_prefix}*.scope"

    def stop_leftovers(self) -> None:
        """Stops engines a worker that died suddenly (a closed terminal, a crash) left running.

        Their task is about to run again: two engines would not fit in the GPU nor in the RAM.
        """
        if not scope_available():
            return
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", self.leftovers_pattern()],
                capture_output=True, timeout=30, check=False,
            )  # fmt: skip
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("could not stop engines left by a previous server")

    def memory_limit(self) -> int:
        if self.settings.memory_max:
            return self.settings.memory_max
        return int(max(total_memory() - GIB, GIB))

    def full_command(self, unit: str, spec_path: Path) -> list[str]:
        base = self.command(spec_path)
        if not scope_available():
            return base
        swap = []
        if self.settings.memory_swap_max is not None:
            swap = ["-p", f"MemorySwapMax={self.settings.memory_swap_max}"]
        return [
            "systemd-run",
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            f"--unit={unit}",
            "-p",
            f"MemoryMax={self.memory_limit()}",
            *swap,
            "--",
            *base,
        ]

    async def run(
        self, job_id: str, spec: dict[str, Any], log: Path, on_event: Callable[[Event], None]
    ) -> Outcome:
        log.parent.mkdir(parents=True, exist_ok=True)
        spec_path = log.parent / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        tmp = self.settings.tmp_dir / job_id
        tmp.mkdir(parents=True, exist_ok=True)
        env = {
            **os.environ,
            "TMPDIR": str(tmp),
            "PYTHONUNBUFFERED": "1",
            # The runner ends itself if this process goes away (see runner.die_with_parent).
            "KARAOKE_PARENT_PID": str(os.getpid()),
        }
        unit = self.unit_for(job_id)
        job = _JobObject(self.memory_limit()) if WINDOWS else None
        with log.open("ab") as stderr:
            process = await asyncio.create_subprocess_exec(
                *self.full_command(unit, spec_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=stderr,
                env=env,
                start_new_session=not WINDOWS,
            )
        if job is not None:
            job.add(process.pid)
        last: Event | None = None
        try:
            assert process.stdout is not None
            while True:
                try:
                    raw = await process.stdout.readline()
                except ValueError:
                    # A line too long for the buffer: some library printing, not an event.
                    continue
                if not raw:
                    break
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("event") in ("done", "error"):
                    last = event
                else:
                    on_event(event)
            code = await process.wait()
        except BaseException:
            # Cancelled, or anything else going wrong here: the task must not keep the GPU.
            await self._stop(unit, process, job)
            raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            if job is not None:
                job.kill()
        return self._outcome(code, last)

    @staticmethod
    def _outcome(code: int, last: Event | None) -> Outcome:
        if last and last.get("event") == "done" and code == 0:
            return Outcome(ok=True, result=dict(last.get("result") or {}))
        if last and last.get("event") == "error":
            return Outcome(
                ok=False,
                code=last.get("code") or "engine_failed",
                message=last.get("message"),
                transient=bool(last.get("transient")),
            )
        if code in KILLED or (WINDOWS and code == JOB_MEMORY_EXIT):
            return Outcome(
                ok=False,
                code="out_of_memory",
                transient=True,
                message="The job ran out of memory and was stopped",
            )
        return Outcome(
            ok=False,
            code="engine_failed",
            transient=True,
            message=f"The engine stopped unexpectedly (exit status {code})",
        )

    async def _stop(
        self, unit: str, process: asyncio.subprocess.Process, job: "_JobObject | None" = None
    ) -> None:
        """SIGTERM to everything the task started, then SIGKILL if it does not go."""
        if job is not None:
            job.kill()
            await process.wait()
            return
        if scope_available():
            await asyncio.to_thread(
                subprocess.run,
                ["systemctl", "--user", "kill", "--signal=SIGTERM", f"{unit}.scope"],
                capture_output=True,
            )
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), KILL_AFTER)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            if scope_available():
                await asyncio.to_thread(
                    subprocess.run,
                    ["systemctl", "--user", "kill", "--signal=SIGKILL", f"{unit}.scope"],
                    capture_output=True,
                )
            await process.wait()
        logger.info("%s stopped", unit)
