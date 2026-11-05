from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from stash.capture import IncomingMessage, ProcessResult, Reply, Reroute
from stash.domain import Item, ItemType, Outcome, RawCapture, Stage
from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitchResult
from stash.lifecycle import Completion, ItemHistory, LibraryEntry, LibraryQuery


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


class LibraryReader(Protocol):
    def library(self, query: LibraryQuery = ...) -> tuple[LibraryEntry, ...]: ...


class ItemLifecycle(LibraryReader, Protocol):
    def complete(
        self,
        item_id: str,
        *,
        rating: int | None = None,
        notes: str = "",
        takeaways: Sequence[str] = (),
        keep: bool | None = None,
        on: date | None = None,
    ) -> Completion: ...

    def annotate(
        self, outcome_id: str, notes: str, takeaways: Sequence[str] | None = None
    ) -> Outcome: ...

    def keep(self, item_id: str, kept: bool) -> Item: ...

    def set_stage(self, item_id: str, stage: Stage, reason: str | None = None) -> Item: ...

    def group(self, child_id: str, parent_id: str) -> Item: ...

    def ungroup(self, child_id: str) -> Item: ...

    def history(self, item_id: str) -> ItemHistory: ...
