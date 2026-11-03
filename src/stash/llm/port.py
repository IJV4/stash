from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from stash.llm.messages import ChatMessage


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ValueError("detail must not be blank")


class ChatModel(Protocol):
    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]: ...


class BusyCheck(Protocol):
    def is_busy(self, now: datetime) -> bool: ...


class ProviderProbe(Protocol):
    def check(self) -> ProbeResult: ...


class ModelUnloader(Protocol):
    def unload(self) -> None: ...
