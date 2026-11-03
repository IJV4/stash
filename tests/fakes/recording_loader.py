from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from stash.config import StashConfig


@dataclass(frozen=True, slots=True)
class LoadCall:
    path: Path
    environment: Mapping[str, str]


class RecordingLoader:
    def __init__(self, config: StashConfig) -> None:
        self._config = config
        self.calls: list[LoadCall] = []

    def __call__(self, path: Path, environment: Mapping[str, str]) -> StashConfig:
        self.calls.append(LoadCall(path, dict(environment)))
        return self._config
