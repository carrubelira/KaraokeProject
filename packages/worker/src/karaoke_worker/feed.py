"""What a task tells the server while it runs: its progress, in order, and its log, live.

Everything goes through one sender per task, so a progress report can never arrive after the
task's completion (the server would take a late report as the task coming back to life), and
`close()` waits for whatever is still on its way before the worker completes or fails the task.
Progress is throttled to one report a second (stage changes always go); log lines go in small
batches. The whole log is also written to a file, uploaded as a blob when the task ends.
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TextIO

from karaoke_contracts.nodes import TaskProgress

logger = logging.getLogger(__name__)

SendProgress = Callable[[TaskProgress], Awaitable[bool]]
SendLines = Callable[[list[str]], Awaitable[None]]

MIN_GAP = 1.0
LOG_BATCH = 50
LOG_EVERY = 0.5


class Feed:
    def __init__(
        self,
        send_progress: SendProgress,
        send_lines: SendLines,
        log_file: Path,
        on_stop: Callable[[], None] = lambda: None,
    ) -> None:
        self._send_progress = send_progress
        self._send_lines = send_lines
        self._on_stop = on_stop
        self.log_file = log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self._log: TextIO = log_file.open("a", encoding="utf-8", errors="replace")
        self._latest: TaskProgress | None = None
        self._sent: TaskProgress | None = None
        self._last_sent = 0.0
        self._lines: list[str] = []
        self._wake = asyncio.Event()
        self._closing = False
        self._sender = asyncio.create_task(self._run(), name="feed")
        self.stage: str | None = None

    # What the task says

    def progress(
        self,
        stage: str,
        fraction: float | None = None,
        step: str | None = None,
        message: str | None = None,
    ) -> None:
        if fraction is not None:
            fraction = min(1.0, max(0.0, fraction))
        if stage != self.stage:
            self.line(f"── {stage}" + (f": {step}" if step else ""))
        self.stage = stage
        self._latest = TaskProgress(stage=stage, fraction=fraction, step=step, message=message)
        self._wake.set()

    def line(self, text: str) -> None:
        for raw in text.split("\n"):
            # A progress bar (tqdm) redraws itself with carriage returns: only its last state.
            part = next((p for p in reversed(raw.split("\r")) if p.strip()), "")
            clean = part.rstrip()
            if not clean:
                continue
            self._log.write(clean + "\n")
            self._lines.append(clean)
        self._log.flush()
        if len(self._lines) >= LOG_BATCH:
            self._wake.set()

    # Sending

    def _due(self) -> bool:
        latest = self._latest
        if latest is None or latest == self._sent:
            return False
        if self._sent is None or latest.stage != self._sent.stage or latest.step != self._sent.step:
            return True
        return time.monotonic() - self._last_sent >= MIN_GAP or latest.fraction in (0.0, 1.0)

    async def _run(self) -> None:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), LOG_EVERY)
            self._wake.clear()
            await self._flush_lines()
            if self._due():
                await self._flush_progress()
            if self._closing and not self._lines:
                return

    async def _flush_lines(self) -> None:
        while self._lines:
            batch, self._lines = self._lines[:LOG_BATCH], self._lines[LOG_BATCH:]
            try:
                await self._send_lines(batch)
            except Exception as exc:  # noqa: BLE001 - the log is a help, never a reason to fail
                logger.debug("log lines not sent: %s", exc)

    async def _flush_progress(self) -> None:
        latest = self._latest
        assert latest is not None
        self._sent, self._last_sent = latest, time.monotonic()
        try:
            keep_going = await self._send_progress(latest)
        except Exception as exc:  # noqa: BLE001 - a lost report is sent again with the next one
            logger.warning("progress not sent: %s", exc)
            self._sent = None
            return
        if not keep_going:
            self._on_stop()

    async def close(self) -> None:
        """Sends what is pending (the last progress included) and stops; call before the task
        is completed or failed."""
        self._closing = True
        self._wake.set()
        try:
            await asyncio.wait_for(asyncio.shield(self._sender), 15)
        except TimeoutError:
            self._sender.cancel()
        if self._latest is not None and self._latest != self._sent:
            with contextlib.suppress(Exception):
                await self._send_progress(self._latest)
        self._log.close()

    def abandon(self) -> None:
        """The task ended without anyone to tell (cancelled): stop sending at once."""
        self._sender.cancel()
        with contextlib.suppress(Exception):
            self._log.close()
