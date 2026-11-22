import os
import subprocess
import sys
import time
from pathlib import Path

import anyio
import pytest

from karaoke_worker.child import ProcessSpawner, scope_available, total_memory
from karaoke_worker.child import SpawnSettings as Settings

pytestmark = pytest.mark.anyio

PYTHON = sys.executable


def alive(pid: int) -> bool:
    """Whether a process is still running. On Windows `os.kill(pid, 0)` would end it."""
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def gone(pid: int) -> bool:
    deadline = time.monotonic() + 10
    while alive(pid) and time.monotonic() < deadline:
        await anyio.sleep(0.1)
    return not alive(pid)


def script(code: str):  # type: ignore[no-untyped-def]
    return lambda spec_path: [PYTHON, "-c", code]


async def test_runs_the_runner_and_reports_events(settings: Settings, tmp_path: Path) -> None:
    spawner = ProcessSpawner(settings)
    events: list[dict[str, object]] = []
    spec = {
        "kind": "make",
        "source": "/x.mp3",
        "out": str(tmp_path / "out"),
        "language": "gl",
        "lyrics": "la",
        "lrclib": False,
        "title": "Proba",
        "artist": None,
        "fake": True,
    }
    outcome = await spawner.run("job-1", spec, tmp_path / "log.txt", events.append)
    assert outcome.ok
    assert [e["stage"] for e in events if e["event"] == "stage"] == [
        "decode",
        "separate",
        "align",
        "encode",
    ]
    assert (tmp_path / "out" / "karaoke.json").is_file()


async def test_a_crash_without_a_report_is_engine_failed(
    settings: Settings, tmp_path: Path
) -> None:
    spawner = ProcessSpawner(
        settings, command=script("import sys; print('boom', file=sys.stderr); sys.exit(3)")
    )
    outcome = await spawner.run("job-1", {}, tmp_path / "log.txt", lambda e: None)
    assert not outcome.ok
    assert outcome.code == "engine_failed"
    assert outcome.transient
    assert "boom" in (tmp_path / "log.txt").read_text()


async def test_spawner_cancel_kills_the_whole_group(settings: Settings, tmp_path: Path) -> None:
    marker = tmp_path / "pids"
    code = (
        "import subprocess, sys, time, pathlib\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(marker)!r}).write_text(str(p.pid))\n"
        "time.sleep(60)\n"
    )
    spawner = ProcessSpawner(settings, command=script(code))

    async def run() -> None:
        await spawner.run("job-1", {}, tmp_path / "log.txt", lambda e: None)

    with anyio.fail_after(20):
        async with anyio.create_task_group() as group:
            group.start_soon(run)
            while not marker.exists():
                await anyio.sleep(0.05)
            group.cancel_scope.cancel()
    assert await gone(int(marker.read_text()))


@pytest.mark.skipif(not scope_available(), reason="needs systemd --user scopes")
async def test_spawner_memory_limit_kills_only_the_child(
    settings: Settings, tmp_path: Path
) -> None:
    limited = Settings(data_dir=settings.data_dir, memory_max=64 * 1024 * 1024, memory_swap_max=0)
    spawner = ProcessSpawner(
        limited, command=script("b = bytearray(512 * 1024 * 1024); print(len(b))")
    )
    outcome = await spawner.run("job-1", {}, tmp_path / "log.txt", lambda e: None)
    assert not outcome.ok
    assert outcome.code == "out_of_memory"
    assert outcome.transient


async def test_child_tmpdir_is_on_disk(settings: Settings, tmp_path: Path) -> None:
    code = (
        "import json, tempfile; print(json.dumps({'event': 'done', 'result': "
        "{'tmp': tempfile.gettempdir()}}))"
    )
    spawner = ProcessSpawner(settings, command=script(code))
    outcome = await spawner.run("job-1", {}, tmp_path / "log.txt", lambda e: None)
    assert outcome.ok
    assert outcome.result["tmp"].startswith(str(settings.tmp_dir))


def test_memory_limit_defaults_to_ram_minus_one_gib(settings: Settings) -> None:
    assert ProcessSpawner(settings).memory_limit() == total_memory() - 1024**3


def test_command_uses_a_scope_when_available(settings: Settings, tmp_path: Path) -> None:
    command = ProcessSpawner(settings).full_command("karaoke-job-1-abc", tmp_path / "spec.json")
    if scope_available():
        assert command[:3] == ["systemd-run", "--user", "--scope"]
        assert any(part.startswith("MemoryMax=") for part in command)
        assert "--unit=karaoke-job-1-abc" in command
    assert command[-3:] == ["-m", "karaoke_worker.runner", str(tmp_path / "spec.json")]


async def test_a_very_long_line_on_stdout_is_skipped(settings: Settings, tmp_path: Path) -> None:
    code = (
        "import json; print('x' * 200_000, flush=True); "
        "print(json.dumps({'event': 'stage', 'stage': 'align'}), flush=True); "
        "print(json.dumps({'event': 'done', 'result': {}}))"
    )
    events: list[dict[str, object]] = []
    spawner = ProcessSpawner(settings, command=script(code))
    with anyio.fail_after(20):
        outcome = await spawner.run("job-1", {}, tmp_path / "log.txt", events.append)
    assert outcome.ok
    assert events == [{"event": "stage", "stage": "align"}]


async def test_the_child_is_stopped_if_the_server_fails_handling_it(
    settings: Settings, tmp_path: Path
) -> None:
    marker = tmp_path / "pid"
    code = (
        "import json, os, pathlib, time\n"
        f"pathlib.Path({str(marker)!r}).write_text(str(os.getpid()))\n"
        "print(json.dumps({'event': 'stage', 'stage': 'align'}), flush=True)\n"
        "time.sleep(60)\n"
    )

    def broken(event: dict[str, object]) -> None:
        raise RuntimeError("the server could not handle the event")

    spawner = ProcessSpawner(settings, command=script(code))
    with anyio.fail_after(20), pytest.raises(RuntimeError):
        await spawner.run("job-1", {}, tmp_path / "log.txt", broken)
    assert await gone(int(marker.read_text()))


def test_engine_units_are_named_after_their_library(settings: Settings, tmp_path: Path) -> None:
    other = Settings(data_dir=tmp_path / "other")
    mine, theirs = ProcessSpawner(settings), ProcessSpawner(other)
    assert mine.unit_for("job1").startswith(mine.unit_prefix + "job1-")
    assert mine.unit_prefix != theirs.unit_prefix
    # Stopping what a dead server left behind never touches another library's jobs.
    assert mine.leftovers_pattern() == mine.unit_prefix + "*.scope"


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="die_with_parent is Linux's; on Windows the spawner's Job Object does it",
)
def test_a_job_process_ends_with_the_server(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    child = (
        "import os, sys, time; from karaoke_worker.runner import die_with_parent;"
        "die_with_parent(); open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(30)"
    )
    # The "server" starts the job, waits until it is under way, and then simply dies.
    parent = (
        "import os, subprocess, sys, time;"
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]],"
        " env={**os.environ, 'KARAOKE_PARENT_PID': str(os.getpid())});"
        "exec('while not os.path.exists(sys.argv[2]) or not open(sys.argv[2]).read():"
        " time.sleep(0.05)')"
    )
    subprocess.run([sys.executable, "-c", parent, child, str(pid_file)], check=True)
    deadline = time.monotonic() + 10
    while not pid_file.exists() or not pid_file.read_text():
        assert time.monotonic() < deadline
        time.sleep(0.05)
    pid = int(pid_file.read_text())
    while alive(pid):
        assert time.monotonic() < deadline, "the job process outlived the server"
        time.sleep(0.05)
