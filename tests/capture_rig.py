from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from builders import BASE
from capture_builders import sequential_ids
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore
from fakes.recording_chat_model import RecordingChatModel
from fakes.scripted_chat_model import ScriptedChatModel
from filing_rig import build_filer
from lifecycle_rig import a_lifecycle
from log_records import recording_logs
from planning_rig import a_planning

from stash.capture import BurstCoalescer, CapturePipeline, FixHandler
from stash.enrich.links import LinkInfo
from stash.llm import LlmError
from stash.planning import Planning

BURST_WINDOW_SECONDS = 5.0
CAPTURE_LOGGER = "stash.capture"


def a_fix_handler(
    store: MemoryStore,
    clock: Callable[[], datetime] = lambda: BASE,
    planning: Planning | None = None,
) -> FixHandler:
    return FixHandler(
        store,
        a_lifecycle(store, clock),
        planning or a_planning(store, FakeChatModel(), clock),
        clock,
    )


def logged_by_applying(store: MemoryStore, data: str) -> list[tuple[int, str]]:
    with recording_logs(CAPTURE_LOGGER) as recorder:
        a_fix_handler(store).apply(data)
    return recorder.entries()


@dataclass(frozen=True, slots=True)
class CaptureRig:
    store: MemoryStore
    inspector: FakeLinkInspector
    model: RecordingChatModel
    busy: FakeBusy
    pipeline: CapturePipeline
    fixes: FixHandler
    bursts: BurstCoalescer

    def set_reply(self, reply: Mapping[str, object]) -> None:
        self._scriptable_model().reply = reply

    def clear_error(self) -> None:
        self._scriptable_model().error = None

    def _scriptable_model(self) -> FakeChatModel:
        if not isinstance(self.model, FakeChatModel):
            raise TypeError("the model cannot be re-scripted: the rig was built with outcomes=")
        return self.model


def build_rig(
    answer: Mapping[str, object] | None = None,
    error: LlmError | None = None,
    links: Mapping[str, LinkInfo] | None = None,
    outcomes: Sequence[Mapping[str, object] | LlmError] | None = None,
    clock: Callable[[], datetime] = lambda: BASE,
) -> CaptureRig:
    if outcomes is not None and (answer is not None or error is not None):
        raise ValueError("outcomes replaces answer and error")
    store = MemoryStore()
    inspector = FakeLinkInspector(links)
    model: RecordingChatModel = (
        FakeChatModel(reply=answer, error=error)
        if outcomes is None
        else ScriptedChatModel(outcomes)
    )
    busy = FakeBusy()
    return CaptureRig(
        store=store,
        inspector=inspector,
        model=model,
        busy=busy,
        pipeline=CapturePipeline(
            store, inspector, build_filer(model, busy, clock), sequential_ids(), clock
        ),
        fixes=a_fix_handler(store, clock),
        bursts=BurstCoalescer(BURST_WINDOW_SECONDS),
    )
