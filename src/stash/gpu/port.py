from dataclasses import dataclass
from typing import Protocol

MAX_PERCENT = 100


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must not be negative, got {value}")


@dataclass(frozen=True, slots=True)
class GpuSample:
    total_mib: int
    used_mib: int
    utilization_pct: int

    def __post_init__(self) -> None:
        _require_non_negative("total_mib", self.total_mib)
        _require_non_negative("used_mib", self.used_mib)
        _require_non_negative("utilization_pct", self.utilization_pct)
        if self.utilization_pct > MAX_PERCENT:
            raise ValueError(f"utilization_pct must be at most {MAX_PERCENT}")

    def foreign_used_mib(self, own_mib: int) -> int:
        _require_non_negative("own_mib", own_mib)
        return max(self.used_mib - own_mib, 0)

    def free_mib(self, own_mib: int) -> int:
        return self.total_mib - self.foreign_used_mib(own_mib)

    def utilization_exceeds(self, limit_pct: int) -> bool:
        return self.utilization_pct > limit_pct


class GpuProbe(Protocol):
    def sample(self) -> GpuSample | None: ...


class OwnVramUsage(Protocol):
    def own_mib(self) -> int: ...


class NoOwnVram:
    def own_mib(self) -> int:
        return 0
