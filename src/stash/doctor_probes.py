from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stash.config import StashConfig
from stash.gpu import GpuProbe
from stash.llm import ProbeResult
from stash.store import ItemStore


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
