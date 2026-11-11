from dataclasses import dataclass
from enum import StrEnum

from stash.domain import Item, RawCapture


class DeferralReason(StrEnum):
    GPU_BUSY = "gpu_busy"
    AI_UNAVAILABLE = "ai_unavailable"
    UNEXPECTED = "unexpected"


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
