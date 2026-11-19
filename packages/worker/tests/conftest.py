from pathlib import Path

import pytest

from karaoke_worker.child import SpawnSettings


@pytest.fixture
def settings(tmp_path: Path) -> SpawnSettings:
    made = SpawnSettings(data_dir=tmp_path / "data")
    made.tmp_dir.mkdir(parents=True)
    return made


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
