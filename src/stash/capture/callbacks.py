from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from stash.domain import MAX_RATING, MIN_RATING
from stash.domain.wire import SEPARATOR, is_wire_safe

TELEGRAM_CALLBACK_LIMIT = 64
PREFIX = "stash"
MIN_PARTS = 3
WIRE_RULE = "must be non-blank, printable ASCII, without whitespace or ':'"


class FixKind(StrEnum):
    TYPE_MENU = "t"
    STAGE_MENU = "s"
    SET_TYPE = "T"
    SET_STAGE = "S"
    QUESTION = "q"
    DONE = "d"
    RATE = "r"
    KEEP = "k"
    ACCEPT_STEPS = "a"
    SKIP_STEPS = "n"
    STEP_DONE = "x"
    NOT_HAPPENED = "h"

    @property
    def takes_argument(self) -> bool:
        return self in (FixKind.SET_TYPE, FixKind.SET_STAGE, FixKind.RATE, FixKind.KEEP)


class KeepChoice(StrEnum):
    KEEP = "1"
    NOT_KEEPING = "0"

    @property
    def kept(self) -> bool:
        return self is KeepChoice.KEEP


RATING_ARGUMENTS = MappingProxyType[str, int](
    {str(rating): rating for rating in range(MIN_RATING, MAX_RATING + 1)}
)


def rating_for(argument: str | None) -> int | None:
    return None if argument is None else RATING_ARGUMENTS.get(argument)


@dataclass(frozen=True, slots=True)
class FixAction:
    kind: FixKind
    subject_id: str
    argument: str | None = None

    def __post_init__(self) -> None:
        if not is_wire_safe(self.subject_id):
            raise ValueError(f"fix action subject_id {WIRE_RULE}")
        if self.kind.takes_argument != (self.argument is not None):
            raise ValueError(f"fix action {self.kind.name} argument presence is wrong")
        if self.argument is not None and not is_wire_safe(self.argument):
            raise ValueError(f"fix action argument {WIRE_RULE}")

    def encode(self) -> str:
        parts = [PREFIX, self.kind.value, self.subject_id]
        if self.argument is not None:
            parts.append(self.argument)
        data = SEPARATOR.join(parts)
        if len(data.encode("utf-8")) > TELEGRAM_CALLBACK_LIMIT:
            raise ValueError(f"callback data exceeds {TELEGRAM_CALLBACK_LIMIT} bytes")
        return data

    @classmethod
    def parse(cls, data: str) -> "FixAction | None":
        parts = data.split(SEPARATOR)
        if len(parts) < MIN_PARTS or parts[0] != PREFIX:
            return None
        try:
            kind = FixKind(parts[1])
            subject_id, *arguments = parts[2:]
            if len(arguments) != int(kind.takes_argument):
                return None
            return cls(kind, subject_id, arguments[0] if arguments else None)
        except ValueError:
            return None
