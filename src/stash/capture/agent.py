import logging
from collections.abc import Callable
from datetime import datetime

from stash.capture.message import IncomingMessage
from stash.capture.ports import AgentIntake
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.capture.results import DeferralReason, Deferred, Filed
from stash.domain import RawCapture, SourceRef

logger = logging.getLogger(__name__)

BLANK_TEXT_MESSAGE = "text must not be blank"
TOO_LONG_MESSAGE = f"text and note together must be at most {TELEGRAM_TEXT_LIMIT} characters"
NOTE_SEPARATOR = "\n"
DUPLICATE_MESSAGE = "an agent capture cannot end as Duplicate"
PROCESSING_FAILED_LOG = "agent capture %s failed unexpectedly; left pending"


class AgentCaptureError(RuntimeError):
    pass


class AgentCapture:
    def __init__(
        self,
        intake: AgentIntake,
        new_id: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        self._intake = intake
        self._new_id = new_id
        self._clock = clock

    def file(self, text: str, note: str | None = None) -> Filed | Deferred:
        message = self._message(text, note)
        capture = self._intake.receive(
            IncomingMessage(SourceRef.agent(self._new_id()), message, (), self._clock())
        )
        if capture is None:
            raise AgentCaptureError(DUPLICATE_MESSAGE)
        return self._processed(capture)

    def _processed(self, capture: RawCapture) -> Filed | Deferred:
        try:
            return self._intake.process_agent(capture)
        except Exception:
            logger.exception(PROCESSING_FAILED_LOG, capture.id)
            return Deferred(capture, DeferralReason.UNEXPECTED)

    def _message(self, text: str, note: str | None) -> str:
        if not text.strip():
            raise ValueError(BLANK_TEXT_MESSAGE)
        message = text if note is None or not note.strip() else f"{text}{NOTE_SEPARATOR}{note}"
        if len(message) > TELEGRAM_TEXT_LIMIT:
            raise ValueError(TOO_LONG_MESSAGE)
        return message
