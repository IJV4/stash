from dataclasses import dataclass
from typing import Final, Literal

from stash.domain import Item, RawCapture

DeferralReason = Literal["gpu_busy", "ai_unavailable"]
UNEXPECTED_FAILURE_REASON: Final[DeferralReason] = "ai_unavailable"


@dataclass(frozen=True, slots=True)
class Filed:
    item: Item
    unsure: bool


@dataclass(frozen=True, slots=True)
class IsRequest:
    capture: RawCapture


@dataclass(frozen=True, slots=True)
class Deferred:
    capture: RawCapture
    reason: DeferralReason


@dataclass(frozen=True, slots=True)
class Duplicate:
    pass


ProcessResult = Filed | IsRequest | Deferred | Duplicate
