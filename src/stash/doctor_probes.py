from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from stash.config import StashConfig
from stash.gpu import GpuProbe
from stash.llm import ProbeResult
from stash.store import BACKUP_LAST_SUCCESS_KEY, ItemStore
from stash.store.port import SettingsStore, Store

STALE_BACKUP_AFTER = timedelta(hours=48)
NO_BACKUP_RECORDED = "no backup recorded yet"
SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, slots=True)
class ConfigProbe:
    config: StashConfig

    def check(self) -> ProbeResult:
        return ProbeResult(
            True, f"provider {self.config.llm.provider}, data directory {self.config.data_dir}"
        )


@dataclass(frozen=True, slots=True)
class DatabaseProbe:
    store: ItemStore
    path: Path

    def check(self) -> ProbeResult:
        self.store.list_items(limit=1)
        return ProbeResult(True, f"ready at {self.path}")


@dataclass(frozen=True, slots=True)
class GpuReadingProbe:
    probe: GpuProbe

    def check(self) -> ProbeResult:
        sample = self.probe.sample()
        if sample is None:
            return ProbeResult(False, "no NVIDIA GPU found (nvidia-smi missing or failed)")
        return ProbeResult(
            True,
            f"{sample.used_mib} / {sample.total_mib} MiB in use, {sample.utilization_pct}% busy",
        )


@dataclass(frozen=True, slots=True)
class PackageProbe:
    module: str
    find_spec: Callable[[str], object | None]

    def check(self) -> ProbeResult:
        if self.find_spec(self.module) is None:
            return ProbeResult(False, "not installed")
        return ProbeResult(True, "installed")


@dataclass(frozen=True, slots=True)
class ExecutableProbe:
    name: str
    which: Callable[[str], str | None]
    hint: str

    def check(self) -> ProbeResult:
        found = self.which(self.name)
        if found is None:
            return ProbeResult(False, f"not found on PATH ({self.hint})")
        return ProbeResult(True, found)


@dataclass(frozen=True, slots=True)
class BackupProbe:
    settings: SettingsStore
    clock: Callable[[], datetime]

    def check(self) -> ProbeResult:
        recorded = self.settings.get_setting(BACKUP_LAST_SUCCESS_KEY)
        if recorded is None:
            return ProbeResult(False, NO_BACKUP_RECORDED)
        age = self.clock() - datetime.fromisoformat(recorded)
        if age < STALE_BACKUP_AFTER:
            return ProbeResult(True, f"last success {_hours(age)} ago")
        return ProbeResult(False, f"last success {age.days} days ago")


def _hours(age: timedelta) -> str:
    hours = int(age.total_seconds() // SECONDS_PER_HOUR)
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


@dataclass(frozen=True, slots=True)
class PendingCapturesProbe:
    store: Store

    def check(self) -> ProbeResult:
        pending = self.store.pending_captures()
        if not pending:
            return ProbeResult(True, "none")
        oldest = min(capture.received_at for capture in pending).date().isoformat()
        return ProbeResult(
            False, f"{len(pending)} saved but not filed, oldest {oldest}; run: stash retry"
        )
