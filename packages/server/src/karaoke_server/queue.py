"""The task queue (plan v4 §3): persistent jobs made of chained tasks, leased by workers.

A job is what an operator asks for (make a karaoke, export an MP4); its tasks form a small DAG
(`fetch → make` for a link, `make` for an upload, `render` for an export). A task is `waiting`
until the tasks it depends on are done, then `ready`; a worker leases it (`leased`, then
`running` once it reports), renews the lease with its heartbeat and finishes it with its
outputs (blobs it uploaded first) or a failure.

- **Leases**: a worker that stops renewing loses the task when its lease expires, and the task
  goes back to `ready` for another worker (up to `max_attempts`).
- **Assignment**: priority first (interactive > batch), then capabilities (task kind, internet,
  free VRAM, pinned worker), then data affinity: the worker that made a task's inputs keeps
  them on disk and gets it first.
- **Idempotent**: completing a task twice with the same lease is a no-op; a stale lease is
  refused.
"""

import asyncio
import contextlib
import json
import logging
import secrets
import time
from collections.abc import Callable
from typing import Any, Literal

from karaoke_contracts.nodes import Lease, Task, TaskFailure, TaskKind, TaskProgress, TaskResult
from karaoke_server.auth import Node
from karaoke_server.clock import iso_now
from karaoke_server.db import Database
from karaoke_server.errors import ApiError
from karaoke_server.events import EventHub

logger = logging.getLogger(__name__)

JobKind = Literal["create", "render"]
FINISHED = ("done", "failed", "cancelled")
# Rough VRAM each kind needs (measured by the bench: separator ≈ 3 GB, aligner ≈ 2.1 GB, one
# model at a time; NVENC ≈ 0.5 GB).
VRAM_MB: dict[str, int] = {"fetch": 0, "make": 3200, "package": 0, "render": 600}
INTERACTIVE = 10
BATCH = 0


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class TaskQueue:
    def __init__(
        self,
        db: Database,
        events: EventHub,
        *,
        lease_seconds: float = 30.0,
        on_job_done: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
        blob_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self.db = db
        self.events = events
        self.lease_seconds = lease_seconds
        self.on_job_done = on_job_done
        self.blob_exists = blob_exists or (lambda sha: True)
        self._changed = asyncio.Event()
        self._reaper: asyncio.Task[None] | None = None

    # Jobs

    def create_job(
        self, kind: JobKind, title: str, params: dict[str, Any], *, priority: int = INTERACTIVE
    ) -> dict[str, Any]:
        job_id = _new_id("j")
        now = iso_now()
        with self.db.transaction():
            self.db.execute(
                "INSERT INTO jobs (id, kind, title, state, params, created_at, updated_at)"
                " VALUES (?, ?, ?, 'active', ?, ?, ?)",
                (job_id, kind, title, _dumps(params), now, now),
            )
            for spec in self._plan(kind, params):
                self._insert_task(job_id, spec, priority, now)
        self._wake()
        job = self.job(job_id)
        self.events.publish("job", job=job)
        return job

    def _plan(self, kind: JobKind, params: dict[str, Any]) -> list[dict[str, Any]]:
        if kind == "render":
            return [{"key": "render", "kind": "render", "params": params,
                     "inputs": [params["manifest"]]}]  # fmt: skip
        make_params = {k: v for k, v in params.items() if k != "url"}
        if params.get("url"):
            return [
                {"key": "fetch", "kind": "fetch", "params": {"url": params["url"]},
                 "needs_internet": True},
                {"key": "make", "kind": "make", "params": make_params, "deps": ["fetch"],
                 "needs_internet": bool(params.get("lrclib"))},
            ]  # fmt: skip
        return [
            {"key": "make", "kind": "make", "params": make_params, "inputs": [params["source"]],
             "needs_internet": bool(params.get("lrclib"))},
        ]  # fmt: skip

    def _insert_task(self, job_id: str, spec: dict[str, Any], priority: int, now: str) -> None:
        deps = [f"{job_id}:{key}" for key in spec.get("deps", [])]
        self.db.execute(
            "INSERT INTO tasks (id, job_id, kind, state, deps, params, inputs, priority, vram_mb,"
            " needs_internet, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"{job_id}:{spec['key']}",
                job_id,
                spec["kind"],
                "waiting" if deps else "ready",
                _dumps(deps),
                _dumps(spec.get("params", {})),
                _dumps(spec.get("inputs", [])),
                priority,
                VRAM_MB[spec["kind"]],
                int(spec.get("needs_internet", False)),
                now,
                now,
            ),
        )

    def job(self, job_id: str) -> dict[str, Any]:
        row = self.db.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such job")
        tasks = [self._task_view(t) for t in self.db.query(
            "SELECT * FROM tasks WHERE job_id = ? ORDER BY created_at, id", (job_id,))]  # fmt: skip
        return {
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "state": row["state"],
            "params": json.loads(row["params"]),
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "tasks": tasks,
            "eta": self._job_eta(tasks),
        }

    def jobs(self, *, active_only: bool = False, limit: int = 200) -> list[dict[str, Any]]:
        where = "WHERE state IN ('active', 'paused')" if active_only else ""
        rows = self.db.query(
            f"SELECT id FROM jobs {where} ORDER BY created_at DESC LIMIT ?",  # noqa: S608
            (limit,),
        )
        return [self.job(r["id"]) for r in rows]

    def _task_view(self, row: Any) -> dict[str, Any]:
        elapsed = (
            time.time() - row["started_at"]
            if row["started_at"] and not row["finished_at"]
            else None
        )
        return {
            "id": row["id"],
            "kind": row["kind"],
            "state": row["state"],
            "node_id": row["node_id"],
            "pinned_node": row["pinned_node"],
            "priority": row["priority"],
            "attempts": row["attempts"],
            "stage": row["stage"],
            "fraction": row["fraction"],
            "error": row["error"],
            "error_code": row["error_code"],
            "outputs": json.loads(row["outputs"]),
            "elapsed": elapsed,
            "eta": self._task_eta(row["kind"], row["state"], elapsed, row["fraction"]),
        }

    def _average(self, kind: str) -> float | None:
        rows = self.db.query(
            "SELECT seconds FROM stage_times WHERE kind = ? AND stage = '*' ORDER BY at DESC"
            " LIMIT 20",
            (kind,),
        )
        return sum(r["seconds"] for r in rows) / len(rows) if rows else None

    def _task_eta(
        self, kind: str, state: str, elapsed: float | None, fraction: float | None
    ) -> float | None:
        if state in FINISHED:
            return 0.0
        if elapsed is not None and fraction and fraction > 0.05:
            return max(0.0, elapsed / fraction - elapsed)
        average = self._average(kind)
        if average is None:
            return None
        return max(0.0, average - (elapsed or 0.0))

    @staticmethod
    def _job_eta(tasks: list[dict[str, Any]]) -> float | None:
        etas = [t["eta"] for t in tasks]
        return None if any(e is None for e in etas) else sum(etas)

    def _touch_job(self, job_id: str) -> None:
        self.db.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (iso_now(), job_id))
        self.events.publish("job", job=self.job(job_id))

    def cancel(self, job_id: str) -> dict[str, Any]:
        self.job(job_id)
        with self.db.transaction():
            self.db.execute(
                "UPDATE tasks SET state = 'cancelled', finished_at = ?, updated_at = ?"
                " WHERE job_id = ? AND state NOT IN ('done', 'failed', 'cancelled')",
                (time.time(), iso_now(), job_id),
            )
            self.db.execute("UPDATE jobs SET state = 'cancelled' WHERE id = ?", (job_id,))
        self._touch_job(job_id)
        return self.job(job_id)

    def pause(self, job_id: str) -> dict[str, Any]:
        """Stops new leases; a task already running finishes."""
        self._require_state(job_id, ("active",))
        with self.db.transaction():
            self.db.execute(
                "UPDATE tasks SET state = 'paused' WHERE job_id = ? AND state = 'ready'", (job_id,)
            )
            self.db.execute("UPDATE jobs SET state = 'paused' WHERE id = ?", (job_id,))
        self._touch_job(job_id)
        return self.job(job_id)

    def resume(self, job_id: str) -> dict[str, Any]:
        self._require_state(job_id, ("paused",))
        with self.db.transaction():
            self.db.execute(
                "UPDATE tasks SET state = 'ready' WHERE job_id = ? AND state = 'paused'", (job_id,)
            )
            self.db.execute("UPDATE jobs SET state = 'active' WHERE id = ?", (job_id,))
        self._wake()
        self._touch_job(job_id)
        return self.job(job_id)

    def retry(self, job_id: str) -> dict[str, Any]:
        """A failed or cancelled job runs again from the first task that did not finish."""
        self._require_state(job_id, ("failed", "cancelled"))
        with self.db.transaction():
            for row in self.db.query(
                "SELECT id, deps FROM tasks WHERE job_id = ? AND state != 'done'", (job_id,)
            ):
                deps = json.loads(row["deps"])
                ready = all(self._state(d) == "done" for d in deps)
                self.db.execute(
                    "UPDATE tasks SET state = ?, attempts = 0, error = NULL, error_code = NULL,"
                    " lease_id = NULL, node_id = NULL, finished_at = NULL, stage = NULL,"
                    " fraction = NULL WHERE id = ?",
                    ("ready" if ready else "waiting", row["id"]),
                )
            self.db.execute(
                "UPDATE jobs SET state = 'active', error = NULL WHERE id = ?", (job_id,)
            )
        self._wake()
        self._touch_job(job_id)
        return self.job(job_id)

    def set_priority(self, job_id: str, priority: int) -> dict[str, Any]:
        self.job(job_id)
        self.db.execute(
            "UPDATE tasks SET priority = ? WHERE job_id = ? AND state NOT IN"
            " ('done', 'failed', 'cancelled')",
            (priority, job_id),
        )
        self._touch_job(job_id)
        return self.job(job_id)

    def pin(self, job_id: str, node_id: str | None) -> dict[str, Any]:
        self.job(job_id)
        self.db.execute(
            "UPDATE tasks SET pinned_node = ? WHERE job_id = ? AND state IN"
            " ('waiting', 'ready', 'paused')",
            (node_id, job_id),
        )
        self._wake()
        self._touch_job(job_id)
        return self.job(job_id)

    def _require_state(self, job_id: str, states: tuple[str, ...]) -> None:
        job = self.job(job_id)
        if job["state"] not in states:
            raise ApiError(409, "bad_state", f"The job is {job['state']}")

    def _state(self, task_id: str) -> str | None:
        row = self.db.one("SELECT state FROM tasks WHERE id = ?", (task_id,))
        return row["state"] if row else None

    # Workers

    def _wake(self) -> None:
        self._changed.set()

    async def wait_lease(
        self, node: Node, free_vram_mb: int | None, wait: float, *, busy_playing: bool = False
    ) -> Lease | None:
        """A lease for the best task this worker can take, waiting up to `wait` s for one."""
        deadline = time.monotonic() + wait
        while True:
            lease = self.lease(node, free_vram_mb, busy_playing=busy_playing)
            remaining = deadline - time.monotonic()
            if lease is not None or remaining <= 0:
                return lease
            self._changed.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._changed.wait(), remaining)

    def lease(
        self, node: Node, free_vram_mb: int | None, *, busy_playing: bool = False
    ) -> Lease | None:
        caps = node.capabilities
        vram = free_vram_mb
        if vram is None:
            vram = max((g.vram_total_mb for g in caps.gpus), default=0)
        best: tuple[tuple[int, int, float], Any] | None = None
        for row in self.db.query(
            "SELECT * FROM tasks WHERE state = 'ready' ORDER BY priority DESC, created_at LIMIT 50"
        ):
            if caps.tasks and row["kind"] not in caps.tasks:
                continue
            if row["needs_internet"] and not caps.internet:
                continue
            if row["pinned_node"] and row["pinned_node"] != node.id:
                continue
            if row["vram_mb"] > 0 and (not caps.gpus or row["vram_mb"] > vram):
                continue
            if busy_playing and row["vram_mb"] > 0:
                continue
            score = (row["priority"], self._affinity(row, node.id), -_created(row))
            if best is None or score > best[0]:
                best = (score, row)
        if best is None:
            return None
        row = best[1]
        lease_id = secrets.token_hex(8)
        expires = time.time() + self.lease_seconds
        changed = self.db.execute(
            "UPDATE tasks SET state = 'leased', lease_id = ?, node_id = ?, lease_expires = ?,"
            " attempts = attempts + 1, started_at = ?, updated_at = ? WHERE id = ? AND"
            " state = 'ready'",
            (lease_id, node.id, expires, time.time(), iso_now(), row["id"]),
        )
        if not changed:
            return None
        self._touch_job(row["job_id"])
        from datetime import UTC, datetime

        return Lease(
            task=self._task_spec(row["id"]),
            lease_id=lease_id,
            expires_at=datetime.fromtimestamp(expires, UTC),
            heartbeat_seconds=max(1.0, self.lease_seconds / 3),
        )

    def _affinity(self, row: Any, node_id: str) -> int:
        """How many of the task's dependencies this node ran (their outputs are on its disk)."""
        deps = json.loads(row["deps"])
        if not deps:
            return 0
        marks = ",".join("?" * len(deps))
        found = self.db.one(
            f"SELECT COUNT(*) AS n FROM tasks WHERE id IN ({marks}) AND node_id = ?",  # noqa: S608
            (*deps, node_id),
        )
        return int(found["n"]) if found else 0

    def _task_spec(self, task_id: str) -> Task:
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        assert row is not None
        kind: TaskKind = row["kind"]
        return Task(
            id=row["id"],
            kind=kind,
            job_id=row["job_id"],
            params=json.loads(row["params"]),
            inputs=json.loads(row["inputs"]),
            vram_mb=row["vram_mb"],
            needs_internet=bool(row["needs_internet"]),
            priority=row["priority"],
        )

    def _held(self, task_id: str, lease_id: str, node: Node) -> Any:
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row is None:
            raise ApiError(404, "not_found", "No such task")
        if row["lease_id"] != lease_id or row["node_id"] != node.id:
            raise ApiError(409, "lease_lost", "This lease is no longer yours")
        return row

    def renew(self, node: Node, task_ids: list[str]) -> list[str]:
        """Extends the leases a worker still holds; returns the ids it must stop (cancelled or
        lost)."""
        stop = []
        expires = time.time() + self.lease_seconds
        for task_id in task_ids:
            row = self.db.one("SELECT state, node_id FROM tasks WHERE id = ?", (task_id,))
            if (
                row is None
                or row["node_id"] != node.id
                or row["state"] not in ("leased", "running")
            ):
                stop.append(task_id)
                continue
            self.db.execute("UPDATE tasks SET lease_expires = ? WHERE id = ?", (expires, task_id))
        return stop

    def progress(self, task_id: str, lease_id: str, node: Node, progress: TaskProgress) -> bool:
        """Records progress and renews the lease; returns False if the task was cancelled."""
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row is not None and row["state"] == "cancelled":
            return False
        row = self._held(task_id, lease_id, node)
        self.db.execute(
            "UPDATE tasks SET state = 'running', stage = ?, fraction = ?, lease_expires = ?,"
            " updated_at = ? WHERE id = ?",
            (
                progress.stage,
                progress.fraction,
                time.time() + self.lease_seconds,
                iso_now(),
                task_id,
            ),
        )
        self.events.publish("task", job_id=row["job_id"], task=self._task_view(self._row(task_id)))
        return True

    def _row(self, task_id: str) -> Any:
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        assert row is not None
        return row

    def complete(self, task_id: str, lease_id: str, node: Node, result: TaskResult) -> None:
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row is not None and row["state"] == "done" and row["lease_id"] == lease_id:
            return  # the same completion twice
        row = self._held(task_id, lease_id, node)
        missing = [sha for sha in result.outputs.values() if not self.blob_exists(sha)]
        if missing:
            raise ApiError(409, "missing_blobs", "Upload the outputs first", missing=missing)
        now = time.time()
        with self.db.transaction():
            self.db.execute(
                "UPDATE tasks SET state = 'done', outputs = ?, data = ?, finished_at = ?,"
                " fraction = 1, updated_at = ? WHERE id = ?",
                (_dumps(result.outputs), _dumps(result.data), now, iso_now(), task_id),
            )
            if row["started_at"]:
                self.db.execute(
                    "INSERT INTO stage_times (kind, stage, seconds, at) VALUES (?, '*', ?, ?)",
                    (row["kind"], now - row["started_at"], now),
                )
            self._release_dependents(row["job_id"], task_id, result)
        self._wake()
        self._maybe_finish(row["job_id"])

    def _release_dependents(self, job_id: str, task_id: str, result: TaskResult) -> None:
        kind = task_id.split(":", 1)[1]
        for dependent in self.db.query(
            "SELECT * FROM tasks WHERE job_id = ? AND state = 'waiting'", (job_id,)
        ):
            deps = json.loads(dependent["deps"])
            if task_id not in deps:
                continue
            params = json.loads(dependent["params"])
            params.setdefault("from", {})[kind] = {**result.outputs, **result.data}
            inputs = json.loads(dependent["inputs"]) + list(result.outputs.values())
            ready = all(self._state(d) == "done" for d in deps)
            self.db.execute(
                "UPDATE tasks SET params = ?, inputs = ?, state = ? WHERE id = ?",
                (_dumps(params), _dumps(inputs), "ready" if ready else "waiting", dependent["id"]),
            )

    def _maybe_finish(self, job_id: str) -> None:
        states = {
            r["state"] for r in self.db.query("SELECT state FROM tasks WHERE job_id = ?", (job_id,))
        }
        if states == {"done"}:
            job = self.job(job_id)
            outputs: dict[str, Any] = {}
            for task in job["tasks"]:
                outputs.update(task["outputs"])
            result = {"outputs": outputs}
            if self.on_job_done is not None:
                try:
                    extra = self.on_job_done({**job, "result": result})
                except ApiError as exc:
                    self.db.execute(
                        "UPDATE jobs SET state = 'failed', error = ? WHERE id = ?",
                        (exc.detail, job_id),
                    )
                    self._touch_job(job_id)
                    return
                result.update(extra or {})
            self.db.execute(
                "UPDATE jobs SET state = 'done', result = ? WHERE id = ?", (_dumps(result), job_id)
            )
        self._touch_job(job_id)

    def fail(self, task_id: str, lease_id: str, node: Node, failure: TaskFailure) -> None:
        row = self._held(task_id, lease_id, node)
        self._failed(row, failure.code, failure.message, failure.retryable)

    def _failed(self, row: Any, code: str, message: str, retryable: bool) -> None:
        again = retryable and row["attempts"] < row["max_attempts"]
        with self.db.transaction():
            if again:
                self.db.execute(
                    "UPDATE tasks SET state = 'ready', lease_id = NULL, node_id = NULL,"
                    " error = ?, error_code = ?, stage = NULL, fraction = NULL, updated_at = ?"
                    " WHERE id = ?",
                    (message, code, iso_now(), row["id"]),
                )
            else:
                self.db.execute(
                    "UPDATE tasks SET state = 'failed', error = ?, error_code = ?,"
                    " finished_at = ?, updated_at = ? WHERE id = ?",
                    (message, code, time.time(), iso_now(), row["id"]),
                )
                self.db.execute(
                    "UPDATE tasks SET state = 'cancelled' WHERE job_id = ? AND state = 'waiting'",
                    (row["job_id"],),
                )
                self.db.execute(
                    "UPDATE jobs SET state = 'failed', error = ? WHERE id = ?",
                    (message, row["job_id"]),
                )
        if again:
            self._wake()
        self._touch_job(row["job_id"])

    def expire(self, now: float | None = None) -> int:
        """Leases nobody renewed: the task goes to another worker (or fails after the last try)."""
        now = time.time() if now is None else now
        expired = self.db.query(
            "SELECT * FROM tasks WHERE state IN ('leased', 'running') AND lease_expires < ?", (now,)
        )
        for row in expired:
            logger.warning("worker %s lost task %s", row["node_id"], row["id"])
            self._failed(row, "worker_lost", "The worker stopped answering", retryable=True)
        return len(expired)

    async def reap_forever(self, every: float = 1.0) -> None:
        while True:
            try:
                self.expire()
            except Exception:
                logger.exception("could not expire leases")
            await asyncio.sleep(every)

    def start(self) -> None:
        self._reaper = asyncio.create_task(self.reap_forever())

    async def stop(self) -> None:
        if self._reaper is not None:
            self._reaper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reaper


def _created(row: Any) -> float:
    from datetime import datetime

    return datetime.fromisoformat(row["created_at"]).timestamp()
