"""The audio engine's keeper (decision 011): the server runs `kp-audio` and runs it again if it
dies.

`kp-audio` is a process of its own, so an audio driver that crashes never takes the API down,
and its real-time threads are never held up by Python. It connects back to the server on the
loopback with a secret made at every start, reads the blobs straight from the server's disk and
sends each stem to the sound cards the routing names.
"""

import asyncio
import contextlib
import logging
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Waits between restarts, in seconds; a run that lasted a minute starts the count again.
BACKOFF = (1, 2, 5, 10, 30)


def find_engine(setting: str) -> Path | None:
    """`auto` looks on the PATH and next to the server's own executable; else it is a path."""
    if setting == "auto":
        name = "kp-audio.exe" if os.name == "nt" else "kp-audio"
        beside = Path(sys.executable).parent / name
        found = shutil.which("kp-audio")
        return Path(found) if found else beside if beside.is_file() else None
    path = Path(setting)
    return path if path.is_file() else None


class AudioEngine:
    def __init__(
        self,
        executable: Path,
        *,
        server: str,
        token: str,
        store: Path,
        on_fault: Callable[[str | None], None],
        backoff: tuple[float, ...] = BACKOFF,
    ) -> None:
        self.executable = executable
        # --watch-stdin: kp-audio stops when our end of its stdin closes, even if we are killed.
        self.args = ("run", "--server", server, "--store", str(store), "--watch-stdin")
        self.token = token
        self.on_fault = on_fault
        self.backoff = backoff
        self._task: asyncio.Task[None] | None = None
        self._process: asyncio.subprocess.Process | None = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._keep())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self._end()

    async def _keep(self) -> None:
        failures = 0
        loop = asyncio.get_running_loop()
        while True:
            started = loop.time()
            try:
                code = await self._run()
            except OSError as exc:
                self.on_fault(f"kp-audio did not start: {exc}")
                code = None
            if loop.time() - started > 60:
                failures = 0
            wait = self.backoff[min(failures, len(self.backoff) - 1)]
            failures += 1
            logger.warning("kp-audio ended (%s); again in %s s", code, wait)
            if failures >= 3:
                self.on_fault(f"kp-audio keeps stopping (last exit {code})")
            await asyncio.sleep(wait)

    async def _run(self) -> int:
        env = {**os.environ, "KARAOKE_AUDIO_TOKEN": self.token}
        self._process = await asyncio.create_subprocess_exec(
            self.executable,
            *self.args,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("kp-audio started (pid %s)", self._process.pid)
        assert self._process.stderr is not None
        async for raw in self._process.stderr:
            line = raw.decode("utf-8", "replace").rstrip()
            if line:
                logger.info("kp-audio: %s", line)
        return await self._process.wait()

    async def _end(self) -> None:
        process = self._process
        if process is None or process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError:
            process.kill()
            await process.wait()
