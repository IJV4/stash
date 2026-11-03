from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

from stash.capture import BurstCoalescer, CaptureIntake, FixHandler
from stash.config import ProviderName, StashConfig
from stash.doctor import Doctor
from stash.evaluation import EvalTarget, Ocr
from stash.gpu import GpuGate
from stash.gpu_switch import GpuSwitch
from stash.llm import ModelRouter
from stash.store import BackupWriter, Closeable, Store


@dataclass(frozen=True, slots=True)
class StashApp:
    config: StashConfig
    store: Store
    pipeline: CaptureIntake
    fixes: FixHandler
    gpu: GpuGate
    gpu_switch: GpuSwitch
    router: ModelRouter
    doctor: Doctor
    burst_factory: Callable[[], BurstCoalescer]
    clock: Callable[[], datetime]
    eval_targets: Mapping[ProviderName, EvalTarget]
    ocr: Ocr
    backups: BackupWriter
    resources: Closeable

    def __post_init__(self) -> None:
        object.__setattr__(self, "eval_targets", MappingProxyType(dict(self.eval_targets)))

    def local_now(self) -> datetime:
        return self.clock().astimezone(self.config.timezone)

    def today(self) -> date:
        return self.local_now().date()

    def close(self) -> None:
        self.resources.close()
