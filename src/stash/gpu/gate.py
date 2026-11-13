from dataclasses import dataclass
from datetime import datetime, timedelta

from stash.config import WHEN_UNREADABLE_BUSY, GpuConfig
from stash.gpu.override import ManualOverride
from stash.gpu.port import GpuProbe, GpuSample, OwnVramUsage
from stash.store.port import SettingsStore

EXPIRY_FORMAT = "%H:%M"
NO_GPU_INFO = "no GPU info"
NO_GPU_READING = "no GPU reading (nvidia-smi unavailable or unreadable); treated as busy"
GPU_IS_FREE = "GPU is free"


@dataclass(frozen=True, slots=True)
class GpuStatus:
    busy: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("reason must not be blank")


def _switched_off(expiry: datetime, now: datetime) -> GpuStatus:
    local_expiry = expiry.astimezone(now.tzinfo)
    return GpuStatus(True, f"turned off until {local_expiry:{EXPIRY_FORMAT}}")


class GpuGate:
    def __init__(
        self,
        probe: GpuProbe,
        own: OwnVramUsage,
        store: SettingsStore,
        config: GpuConfig,
    ) -> None:
        self._probe = probe
        self._own = own
        self._config = config
        self._override = ManualOverride(store, timedelta(hours=config.manual_off_hours))

    def turn_off(self, now: datetime) -> datetime:
        return self._override.off(now)

    def turn_on(self) -> None:
        self._override.on()

    def is_busy(self, now: datetime) -> bool:
        return self.status(now).busy

    def status(self, now: datetime) -> GpuStatus:
        expiry = self._override.active_until(now)
        if expiry is not None:
            return _switched_off(expiry, now)
        sample = self._probe.sample()
        if sample is None:
            if self._config.when_unreadable == WHEN_UNREADABLE_BUSY:
                return GpuStatus(True, NO_GPU_READING)
            return GpuStatus(False, NO_GPU_INFO)
        return self._judge(sample)

    def _judge(self, sample: GpuSample) -> GpuStatus:
        own_mib = self._own.own_mib()
        own_model_loaded = own_mib > 0
        if sample.free_mib(own_mib) < self._config.min_free_vram_mib:
            return GpuStatus(True, f"other apps use {sample.foreign_used_mib(own_mib)} MiB")
        if not own_model_loaded and sample.utilization_exceeds(
            self._config.max_foreign_utilization_pct
        ):
            return GpuStatus(True, f"GPU {sample.utilization_pct}% busy")
        return GpuStatus(False, GPU_IS_FREE)
