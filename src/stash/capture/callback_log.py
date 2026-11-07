import logging
from dataclasses import dataclass
from enum import StrEnum

MAX_LOGGED_CALLBACK_CHARS = 64


class Subject(StrEnum):
    ITEM = "item"
    OUTCOME = "outcome"
    CAPTURE = "capture"
    STEP = "step"


def _clamped(value: str | None) -> str | None:
    return None if value is None else value[:MAX_LOGGED_CALLBACK_CHARS]


@dataclass(frozen=True, slots=True)
class CallbackLog:
    logger: logging.Logger

    def unparseable(self, data: str) -> None:
        self.logger.warning("unparseable fix callback: %r", _clamped(data))

    def unknown(self, subject: Subject, subject_id: str) -> None:
        self.logger.info("fix callback for unknown %s %s", subject, _clamped(subject_id))

    def changed(self, subject: Subject, subject_id: str) -> None:
        self.logger.info("fix callback for %s %s changed meanwhile", subject, _clamped(subject_id))

    def busy(self) -> None:
        self.logger.warning("fix callback while the stash was busy")

    def invalid(self, subject: Subject, subject_id: str, kind: str, value: str | None) -> None:
        self.logger.warning(
            "fix callback for %s %s has an invalid %s %r",
            subject,
            _clamped(subject_id),
            kind,
            _clamped(value),
        )
