from datetime import datetime
from typing import Protocol

from stash.capture import IncomingMessage, ProcessResult, Reply, Reroute
from stash.domain import Item, ItemType, RawCapture, Stage
from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitchResult


class IntakeSteps(Protocol):
    def receive(self, message: IncomingMessage) -> RawCapture | None: ...

    def process(self, capture: RawCapture) -> ProcessResult: ...


class Retrier(Protocol):
    def retry_pending(self) -> list[ProcessResult]: ...


class FixApplier(Protocol):
    def apply(self, data: str) -> Reply | Reroute: ...


class GpuControl(Protocol):
    def status(self, now: datetime) -> GpuStatus: ...

    def turn_off(self, now: datetime) -> GpuSwitchResult: ...

    def turn_on(self) -> None: ...


class ItemReader(Protocol):
    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = ...,
        offset: int = 0,
    ) -> list[Item]: ...

    def search_items(self, query: str, limit: int = ...) -> list[Item]: ...
