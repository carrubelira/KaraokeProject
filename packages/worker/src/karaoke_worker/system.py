"""What this machine is (capabilities) and how busy it is (telemetry), sent to the server.

GPU figures come from NVML (`nvidia-ml-py`) when an NVIDIA driver is there; without one the
worker still runs CPU tasks (downloads).
"""

import logging
import os
import shutil
import sys
from typing import Any

from karaoke_contracts.nodes import Capabilities, Gpu, Telemetry
from karaoke_worker.child import total_memory

logger = logging.getLogger(__name__)
MIB = 1024 * 1024


def _os() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _nvml() -> Any | None:
    try:
        import pynvml

        pynvml.nvmlInit()
    except Exception:  # noqa: BLE001 - no driver, no library, no GPU: all mean "none"
        return None
    return pynvml


def gpus() -> list[Gpu]:
    nvml = _nvml()
    if nvml is None:
        return []
    found = []
    for index in range(nvml.nvmlDeviceGetCount()):
        handle = nvml.nvmlDeviceGetHandleByIndex(index)
        name = nvml.nvmlDeviceGetName(handle)
        memory = nvml.nvmlDeviceGetMemoryInfo(handle)
        found.append(
            Gpu(
                name=name if isinstance(name, str) else name.decode(),
                vram_total_mb=memory.total // MIB,
            )
        )
    return found


def model_versions() -> dict[str, str]:
    """The engine's pieces that change results: the server may require a minimum."""
    from importlib import metadata

    versions = {"engine": metadata.version("karaoke-engine")}
    try:
        from karaoke_engine.align.aligner import LyricsAligner
        from karaoke_engine.transcribe import WhisperTranscriber

        versions["aligner"] = str(getattr(LyricsAligner, "version", "?"))
        versions["transcriber"] = str(getattr(WhisperTranscriber, "version", "?"))
    except ImportError:
        pass
    return versions


def capabilities(tasks: list[str], internet: bool, same_host: bool = False) -> Capabilities:
    kinds = [t for t in tasks if t != "fetch" or (internet and shutil.which("uvx") is not None)]
    return Capabilities(
        os=_os(),  # type: ignore[arg-type]
        cpus=os.cpu_count() or 1,
        ram_mb=total_memory() // MIB,
        gpus=gpus(),
        internet=internet,
        tasks=kinds,  # type: ignore[arg-type]
        models=model_versions(),
        same_host_as_server=same_host,
    )


def telemetry() -> Telemetry:
    data: dict[str, Any] = {}
    nvml = _nvml()
    if nvml is not None and nvml.nvmlDeviceGetCount():
        handle = nvml.nvmlDeviceGetHandleByIndex(0)
        memory = nvml.nvmlDeviceGetMemoryInfo(handle)
        data["vram_used_mb"] = memory.used // MIB
        data["vram_free_mb"] = memory.free // MIB
        try:
            data["gpu_util"] = float(nvml.nvmlDeviceGetUtilizationRates(handle).gpu)
            data["gpu_temp_c"] = float(nvml.nvmlDeviceGetTemperature(handle, 0))
        except Exception:  # noqa: BLE001 - some boards do not report these
            logger.debug("no utilisation or temperature from NVML")
    if hasattr(os, "getloadavg"):
        data["cpu_util"] = min(100.0, os.getloadavg()[0] / (os.cpu_count() or 1) * 100)
    return Telemetry.model_validate(data)
