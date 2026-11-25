"""The server's clocks.

`now_us()` is the stage's timeline (decision 011): every anchor, every `time` answer and every
instant a screen or `kp-audio` schedules for is on it. It is **monotonic**, so NTP never steps or
slews it and an anchor set 120 ms ahead lands 120 ms ahead; and it is the system's fine counter
(`perf_counter`: QueryPerformanceCounter on Windows, CLOCK_MONOTONIC elsewhere). On Windows,
Python 3.12's `time.monotonic` ticks every 15.6 ms and drifts hundreds of ppm from it, which
the screens measured. The wall clock is only for what a person reads (`iso_now`).
"""

import time
from datetime import UTC, datetime


def now_us() -> int:
    return time.perf_counter_ns() // 1000


def iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
