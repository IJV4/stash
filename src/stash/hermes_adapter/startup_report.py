import logging
from collections.abc import Callable
from datetime import datetime

from stash.gpu.gate import NO_GPU_READING, GpuStatus

READING_LOG = "stash GPU gate at start: busy=%s (%s)"
UNREADABLE_WARNING = (
    "stash cannot read the GPU from this service (is nvidia-smi on the service PATH?)"
)
REPORT_FAILED_LOG = "could not report the GPU reading at start"


def log_gpu_reading(
    status: Callable[[datetime], GpuStatus], now: datetime, log: logging.Logger
) -> None:
    try:
        reading = status(now)
        log.info(READING_LOG, reading.busy, reading.reason)
        if reading.busy and reading.reason == NO_GPU_READING:
            log.warning(UNREADABLE_WARNING)
    except Exception:
        log.exception(REPORT_FAILED_LOG)
