import asyncio
import logging
from collections.abc import Coroutine
from typing import assert_never

from stash.capture import (
    DeferralReason,
    Deferred,
    Duplicate,
    Filed,
    IsRequest,
    ProcessResult,
    Reply,
)
from stash.domain import RawCapture
from stash.hermes_adapter.bursts import Bursts
from stash.hermes_adapter.events import (
    Chat,
    EventTranslator,
    HermesEvent,
    Inbound,
    Passthrough,
    Verdict,
)
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.ports import IntakeSteps

logger = logging.getLogger(__name__)

SAVE_FAILED = Reply("⚠️ I could not save that message — please send it again.")
PROCESSING_FAILED_LOG = "processing capture %s failed"
QUEUE_FAILED_LOG = "could not queue the saved reply for capture %s"


class MessageIntake:
    def __init__(
        self,
        translator: EventTranslator,
        steps: IntakeSteps,
        bursts: Bursts,
        sender: ReplySender,
    ) -> None:
        self._translator = translator
        self._steps = steps
        self._bursts = bursts
        self._sender = sender
        self._in_flight: set[asyncio.Task[Verdict]] = set()

    async def on_dispatch(
        self,
        event: HermesEvent,
        gateway: object = None,
        session_store: object = None,
        **kwargs: object,
    ) -> dict[str, str]:
        read = self._read(event)
        if isinstance(read, Passthrough):
            return Verdict.ALLOW.hook_result()
        capture = await self._received(read)
        if capture is None:
            return Verdict.SKIP.hook_result()
        return (await self._shielded(self._classified(capture, read))).hook_result()

    def _read(self, event: HermesEvent) -> Inbound | Passthrough:
        try:
            return self._translator.read(event)
        except Exception:
            logger.exception("could not read a gateway event")
            return Passthrough()

    async def _received(self, inbound: Inbound) -> RawCapture | None:
        try:
            return await asyncio.to_thread(self._steps.receive, inbound.message)
        except Exception:
            logger.exception(
                "could not save message %s from chat %s",
                inbound.message.source.message_id,
                inbound.chat.chat_id,
            )
            await self._apologise(inbound.chat)
            return None

    async def _apologise(self, chat: Chat) -> None:
        try:
            await self._sender.send(chat.chat_id, SAVE_FAILED)
        except Exception:
            logger.exception("could not apologise to chat %s", chat.chat_id)

    async def _shielded(self, work: Coroutine[None, None, Verdict]) -> Verdict:
        task = asyncio.create_task(work)
        self._in_flight.add(task)
        task.add_done_callback(self._in_flight.discard)
        return await asyncio.shield(task)

    async def _classified(self, capture: RawCapture, inbound: Inbound) -> Verdict:
        try:
            # Unverified, PC check spike-m0 #23: a ~100 s hook (shared link) may time out or delay.
            result = await asyncio.to_thread(self._steps.process, capture)
        except Exception:
            logger.exception(PROCESSING_FAILED_LOG, capture.id)
            self._queue_deferred_reply(capture, inbound.chat)
            return inbound.failure_verdict
        return self._settle_or_fail(result, capture, inbound)

    def _queue_deferred_reply(self, capture: RawCapture, chat: Chat) -> None:
        try:
            self._bursts.add(chat.chat_id, Deferred(capture, DeferralReason.UNEXPECTED))
        except Exception:
            logger.exception(QUEUE_FAILED_LOG, capture.id)

    def _settle_or_fail(
        self, result: ProcessResult, capture: RawCapture, inbound: Inbound
    ) -> Verdict:
        try:
            return self._settle(result, inbound.chat)
        except Exception:
            logger.exception(PROCESSING_FAILED_LOG, capture.id)
            return inbound.failure_verdict

    def _settle(self, result: ProcessResult, chat: Chat) -> Verdict:
        match result:
            case Filed() | Deferred():
                self._bursts.add(chat.chat_id, result)
                return Verdict.SKIP
            case IsRequest():
                return Verdict.ALLOW
            case Duplicate():
                return Verdict.SKIP
            case _:
                assert_never(result)
