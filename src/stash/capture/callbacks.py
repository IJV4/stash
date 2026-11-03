from dataclasses import dataclass
from enum import StrEnum

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

    @property
    def takes_argument(self) -> bool:
        return self in (FixKind.SET_TYPE, FixKind.SET_STAGE)


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
