"""The worker's main loop (plan v4 §4): heartbeat, lease, run, report, repeat.

Connections go out from the worker, so it works behind NAT and over Tailscale. It holds at most
one GPU task (concurrency by VRAM: on a 4 GB card one model fits) and a couple of CPU tasks
(downloads) at once. Every call to the server runs in a thread, so a long upload never stops
the heartbeat that keeps its leases alive.
"""

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from karaoke_contracts.nodes import Heartbeat, Lease, TaskFailure, TaskProgress, TaskResult
from karaoke_worker import system, tasks
from karaoke_worker.feed import Feed
from karaoke_worker.tasks import Context, TaskError

logger = logging.getLogger(__name__)

CPU_SLOTS = 2


@dataclass
class Running:
    lease: Lease
    task: "asyncio.Task[None]"
    gpu: bool


@dataclass
class Agent:
    ctx: Context
    player_lock: Path | None = None
    heartbeat_seconds: float = 5.0
    retry_seconds: float = 3.0
    running: dict[str, Running] = field(default_factory=dict)
    lease_wait: bool = True

    def busy_playing(self) -> bool:
        if self.player_lock is None:
            return False
        try:
            return time.time() - self.player_lock.stat().st_mtime < 10
        except OSError:
            return False

    def _gpu_busy(self) -> bool:
        return any(r.gpu for r in self.running.values())

    def _cpu_busy(self) -> int:
        return sum(1 for r in self.running.values() if not r.gpu)

    async def heartbeat_once(self) -> None:
        beat = Heartbeat(
            telemetry=await asyncio.to_thread(system.telemetry),
            running=list(self.running),
            busy_playing=self.busy_playing(),
        )
        answer = await asyncio.to_thread(self.ctx.client.heartbeat, beat)
        for task_id in answer.get("stop", []):
            running = self.running.get(task_id)
            if running is not None:
                logger.info("the server stopped %s", task_id)
                running.task.cancel()

    async def _heartbeats(self) -> None:
        while True:
            try:
                await self.heartbeat_once()
            except (httpx.HTTPError, OSError) as exc:
                logger.warning("heartbeat failed: %s", exc)
            await asyncio.sleep(self.heartbeat_seconds)

    async def lease_once(self) -> Lease | None:
        if self._gpu_busy() and self._cpu_busy() >= CPU_SLOTS:
            return None
        telemetry = await asyncio.to_thread(system.telemetry)
        # Without NVML (a fake engine, a machine without a driver) the server uses the total.
        free = 0 if self._gpu_busy() else telemetry.vram_free_mb
        lease = await asyncio.to_thread(
            self.ctx.client.lease, free, self.busy_playing(), self.lease_wait
        )
        if lease is not None:
            self.start(lease)
        return lease

    def start(self, lease: Lease) -> None:
        gpu = lease.task.vram_mb > 0
        task = asyncio.create_task(self._run(lease), name=lease.task.id)
        self.running[lease.task.id] = Running(lease, task, gpu)

    async def _run(self, lease: Lease) -> None:
        task_id = lease.task.id
        logger.info("running %s (%s)", task_id, lease.task.kind)
        client = self.ctx.client

        async def send_progress(progress: TaskProgress) -> bool:
            return await asyncio.to_thread(client.progress, lease, progress)

        async def send_lines(lines: list[str]) -> None:
            await asyncio.to_thread(client.log, lease, lines)

        def stop() -> None:
            running = self.running.get(task_id)
            if running is not None:
                logger.info("the server stopped %s", task_id)
                running.task.cancel()

        log_file = self.ctx.work / "logs" / f"{task_id.replace(':', '-')}.log"
        log_file.unlink(missing_ok=True)
        feed = Feed(send_progress, send_lines, log_file, stop)
        try:
            result = await tasks.run(self.ctx, lease, feed)
            await feed.close()
            log = await self._upload_log(log_file)
            if log is not None:
                result = TaskResult(outputs={**result.outputs, "log": log}, data=result.data)
            await asyncio.to_thread(client.complete, lease, result)
            logger.info("%s done", task_id)
        except asyncio.CancelledError:
            feed.abandon()
            logger.info("%s cancelled", task_id)
        except Exception as exc:
            if isinstance(exc, TaskError):
                failure = TaskFailure(code=exc.code, message=str(exc), retryable=exc.retryable)
            else:
                logger.exception("%s failed", task_id)
                failure = TaskFailure(code="engine_failed", message=str(exc)[:500])
            feed.line(f"✖ {failure.code}: {failure.message}")
            await feed.close()
            log = await self._upload_log(log_file)
            await self._fail(lease, failure.model_copy(update={"log": log}))
        finally:
            self.running.pop(task_id, None)
            log_file.unlink(missing_ok=True)

    async def _upload_log(self, log_file: Path) -> str | None:
        """The task's whole log goes up as a blob, so it can be read after the task is gone."""

        def has_lines() -> bool:
            return log_file.is_file() and log_file.stat().st_size > 0

        if not await asyncio.to_thread(has_lines):
            return None
        try:
            return await asyncio.to_thread(self.ctx.client.upload, log_file)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("the log of %s did not go up: %s", log_file.stem, exc)
            return None

    async def _fail(self, lease: Lease, failure: TaskFailure) -> None:
        try:
            await asyncio.to_thread(self.ctx.client.fail, lease, failure)
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("could not report the failure of %s: %s", lease.task.id, exc)

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        stop = stop or asyncio.Event()
        self.ctx.spawner.stop_leftovers()
        beats = asyncio.create_task(self._heartbeats())
        try:
            while not stop.is_set():
                try:
                    lease = await self.lease_once()
                except (httpx.HTTPError, OSError) as exc:
                    logger.warning("the server is not answering: %s", exc)
                    lease = None
                    await asyncio.sleep(self.retry_seconds)
                if lease is None:
                    # Nothing to do (the server held the request) or no free slot.
                    await asyncio.sleep(0.5 if self.running else 0.05)
        finally:
            beats.cancel()
            for running in list(self.running.values()):
                running.task.cancel()
            with contextlib.suppress(BaseException):
                await asyncio.gather(beats, *(r.task for r in self.running.values()))
