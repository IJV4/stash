import asyncio
import logging
from typing import assert_never

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult, Reply
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
        return (await self._verdict(capture, read)).hook_result()

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

    async def _verdict(self, capture: RawCapture, inbound: Inbound) -> Verdict:
        try:
            # Unverified, PC must check spike-m0 #23: a 25-45 s hook may time out or delay others.
            result = await asyncio.to_thread(self._steps.process, capture)
            return self._settle(result, inbound.chat)
        except Exception:
            logger.exception("processing capture %s failed", capture.id)
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
