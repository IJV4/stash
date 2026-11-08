from datetime import date
from typing import Protocol

from stash.capture import IncomingMessage, ProcessResult, Reply, Reroute
from stash.domain import (
    RawCapture,
    Step,
)
from stash.library_html import RenderedLibrary
from stash.suggestions.results import Picked, Unavailable


class IntakeSteps(Protocol):
    def receive(self, message: IncomingMessage) -> RawCapture | None: ...

    def process(self, capture: RawCapture) -> ProcessResult: ...


class FixApplier(Protocol):
    def apply(self, data: str) -> Reply | Reroute: ...


class LibraryDocuments(Protocol):
    def rendered_library(self) -> RenderedLibrary: ...

    def keep_library_copy(self, data: bytes) -> None: ...


class StepPlanner(Protocol):
    def add_step(
        self,
        item_id: str,
        text: str,
        *,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step: ...

    def edit_step(
        self,
        step_id: str,
        *,
        text: str | None = None,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step: ...

    def complete_step(self, step_id: str) -> Step: ...


class Suggester(Protocol):
    def suggest(self, context: str, limit: int) -> Picked | Unavailable: ...
