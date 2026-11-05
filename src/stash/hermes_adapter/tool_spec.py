from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

TOOLSET = "stash"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    schema: Mapping[str, Any]
    handler: Callable[..., str]
