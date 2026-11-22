"""A task's feed: progress in order, throttled, nothing after close, and its log."""

import asyncio
from pathlib import Path

import pytest

from karaoke_contracts.nodes import TaskProgress
from karaoke_worker.feed import Feed

pytestmark = pytest.mark.anyio


async def test_progress_keeps_its_order_and_close_sends_the_last(tmp_path: Path) -> None:
    sent: list[TaskProgress] = []
    lines: list[str] = []

    async def send_progress(progress: TaskProgress) -> bool:
        await asyncio.sleep(0.01)  # a slow server
        sent.append(progress)
        return True

    async def send_lines(batch: list[str]) -> None:
        lines.extend(batch)

    feed = Feed(send_progress, send_lines, tmp_path / "task.log")
    feed.progress("download", 0.1)
    for step in range(20):
        feed.progress("download", 0.1 + step / 40)  # throttled: only some go
    feed.line("[download] 50%")
    feed.progress("upload", 1.0, "source")
    await feed.close()
    stages = [p.stage for p in sent]
    assert stages == sorted(stages, key=lambda s: s == "upload"), "no report out of order"
    assert sent[-1] == TaskProgress(stage="upload", fraction=1.0, step="source")
    assert len(sent) < 10
    assert "[download] 50%" in lines
    assert (tmp_path / "task.log").read_text(encoding="utf-8").splitlines() == [
        "── download",
        "[download] 50%",
        "── upload: source",
    ]


async def test_the_server_can_stop_the_task(tmp_path: Path) -> None:
    stopped = asyncio.Event()

    async def refuse(progress: TaskProgress) -> bool:
        return False

    async def ignore(batch: list[str]) -> None:
        pass

    feed = Feed(refuse, ignore, tmp_path / "task.log", stopped.set)
    feed.progress("separate", 0.3)
    await asyncio.wait_for(stopped.wait(), 5)
    feed.abandon()


async def test_a_progress_bar_redrawn_with_carriage_returns_is_one_line(tmp_path: Path) -> None:
    lines: list[str] = []

    async def send_progress(progress: TaskProgress) -> bool:
        return True

    async def send_lines(batch: list[str]) -> None:
        lines.extend(batch)

    feed = Feed(send_progress, send_lines, tmp_path / "task.log")
    feed.line("\r 10%|█ | 1/10\r 50%|█████ | 5/10\r100%|██████████| 10/10")
    feed.line("done\nnext")
    await feed.close()
    assert lines == ["100%|██████████| 10/10", "done", "next"]
