import asyncio
import logging
from typing import assert_never

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult, Reply
from stash.domain import RawCapture
from stash.hermes_adapter.assistant import Assistant
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
from stash.hermes_adapter.scheduler import Scheduler

logger = logging.getLogger(__name__)

SAVE_FAILED = Reply("⚠️ I could not save that message — please send it again.")


class MessageIntake:
    def __init__(
        self,
        translator: EventTranslator,
        steps: IntakeSteps,
        bursts: Bursts,
        assistant: Assistant,
        sender: ReplySender,
        scheduler: Scheduler,
    ) -> None:
        self._translator = translator
        self._steps = steps
        self._bursts = bursts
        self._assistant = assistant
        self._sender = sender
        self._scheduler = scheduler

    async def on_dispatch(
        self,
        event: HermesEvent,
        gateway: object = None,
        session_store: object = None,
        **kwargs: object,
    ) -> dict[str, str]:
        inbound = self._read(event)
        if not isinstance(inbound, Inbound):
            return Verdict.ALLOW.hook_result()
        capture = await self._received(inbound)
        if capture is not None:
            self._scheduler.spawn(
                self._process(capture, inbound.chat), f"stash-process-{capture.id}"
            )
        return Verdict.SKIP.hook_result()

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

    async def _process(self, capture: RawCapture, chat: Chat) -> None:
        try:
            result = await asyncio.to_thread(self._steps.process, capture)
            await self._route(result, chat)
        except Exception:
            logger.exception("processing capture %s failed", capture.id)

    async def _route(self, result: ProcessResult, chat: Chat) -> None:
        match result:
            case Filed() | Deferred():
                self._bursts.add(chat.chat_id, result)
            case IsRequest(capture):
                await self._assistant.ask(capture.text, chat)
            case Duplicate():
                pass
            case _:
                assert_never(result)
