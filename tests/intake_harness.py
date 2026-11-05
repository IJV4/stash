import asyncio
import threading
from collections.abc import Callable

from builders import BASE
from capture_builders import a_filing_answer, sequential_ids
from capture_rig import CaptureRig, build_rig
from fakes.pausing_scheduler import PausingScheduler
from fakes.recording_sender import RecordingSender
from fakes.scripted_sender import ScriptedSender
from fakes.scripted_steps import ScriptedSteps
from hermes_events import CHAT_ID, OWNER_ID, FakeEvent, an_event
from hermes_rig import until

from stash.capture import BurstCoalescer, ProcessResult
from stash.hermes_adapter.bursts import Bursts
from stash.hermes_adapter.events import EventTranslator
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.owners import Owners


class IntakeHarness:
    def __init__(
        self,
        rig: CaptureRig | None = None,
        *,
        receive_failure: Exception | None = None,
        process_failure: Exception | None = None,
        process_result: ProcessResult | None = None,
        process_gate: threading.Event | None = None,
        burst_failure: Exception | None = None,
        apology_sender: ReplySender | None = None,
    ) -> None:
        self.rig = rig or build_rig(a_filing_answer())
        self.steps = ScriptedSteps(
            self.rig.pipeline,
            receive_failure=receive_failure,
            process_failure=process_failure,
            process_result=process_result,
            process_gate=process_gate,
        )
        self.scheduler = PausingScheduler()
        self.reply_sender = ScriptedSender()
        self.apology_sender = apology_sender or RecordingSender()
        self.intake = MessageIntake(
            EventTranslator(Owners.parse(OWNER_ID), lambda: BASE, sequential_ids()),
            self.steps,
            Bursts(self._burst_factory(burst_failure), self.reply_sender, self.scheduler),
            self.apology_sender,
        )

    def _burst_factory(self, failure: Exception | None) -> Callable[[], BurstCoalescer]:
        def factory() -> BurstCoalescer:
            if failure is not None:
                raise failure
            return self.rig.bursts

        return factory

    def dispatch(self, event: FakeEvent | None = None) -> dict[str, str]:
        verdict = asyncio.run(self.intake.on_dispatch(event or an_event(chat_id=CHAT_ID)))
        self.scheduler.abandon()
        return verdict

    def dispatch_and_drain(self, event: FakeEvent | None = None) -> dict[str, str]:
        async def scenario() -> dict[str, str]:
            verdict = await self.intake.on_dispatch(event or an_event(chat_id=CHAT_ID))
            await self.scheduler.drain()
            return verdict

        return asyncio.run(scenario())

    async def cancel_mid_classification(
        self, gate: threading.Event
    ) -> asyncio.Task[dict[str, str]]:
        task = asyncio.create_task(self.intake.on_dispatch(an_event(chat_id=CHAT_ID)))
        await until(lambda: self.steps.processed)
        task.cancel()
        gate.set()
        await asyncio.wait([task])
        await until(lambda: self.scheduler.spawned)
        await self.scheduler.drain()
        return task
