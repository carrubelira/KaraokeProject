"""The server keeps kp-audio running: it starts it, starts it again, and says when it cannot."""

import asyncio
import sys
from pathlib import Path

from karaoke_server.audio import AudioEngine, find_engine


def test_an_engine_that_keeps_stopping_is_reported(tmp_path: Path) -> None:
    faults: list[str | None] = []

    async def main() -> None:
        # Python with kp-audio's arguments: it exits at once with an error, every time.
        engine = AudioEngine(
            Path(sys.executable),
            server="http://127.0.0.1:1",
            token="t",
            store=tmp_path,
            on_fault=faults.append,
            backoff=(0.01,),
        )
        engine.start()
        for _ in range(500):
            if faults:
                break
            await asyncio.sleep(0.01)
        await engine.stop()

    asyncio.run(main())
    assert faults
    assert faults[0] is not None
    assert "keeps stopping" in faults[0]


def test_the_engine_is_found_by_path_or_not_at_all(tmp_path: Path) -> None:
    assert find_engine(str(tmp_path / "missing")) is None
    exe = tmp_path / "kp-audio"
    exe.write_bytes(b"")
    assert find_engine(str(exe)) == exe
