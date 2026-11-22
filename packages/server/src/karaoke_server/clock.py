"""The server's clock: every anchor and command uses it, in microseconds since the epoch."""

import time
from datetime import UTC, datetime


def now_us() -> int:
    return time.time_ns() // 1000


def iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
