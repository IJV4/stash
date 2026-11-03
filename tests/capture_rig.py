from collections.abc import Mapping
from dataclasses import dataclass

from builders import BASE
from capture_builders import sequential_ids
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore
from filing_rig import build_filer

from stash.capture import BurstCoalescer, CapturePipeline, FixHandler
from stash.enrich.links import LinkInfo
from stash.llm import LlmError

BURST_WINDOW_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class CaptureRig:
    store: MemoryStore
    inspector: FakeLinkInspector
    model: FakeChatModel
    busy: FakeBusy
    pipeline: CapturePipeline
    fixes: FixHandler
    bursts: BurstCoalescer


def build_rig(
    answer: Mapping[str, object] | None = None,
    error: LlmError | None = None,
    links: Mapping[str, LinkInfo] | None = None,
) -> CaptureRig:
    store = MemoryStore()
    inspector = FakeLinkInspector(links)
    model = FakeChatModel(reply=answer, error=error)
    busy = FakeBusy()
    clock = lambda: BASE  # noqa: E731
    return CaptureRig(
        store=store,
        inspector=inspector,
        model=model,
        busy=busy,
        pipeline=CapturePipeline(
            store, inspector, build_filer(model, busy, clock), sequential_ids(), clock
        ),
        fixes=FixHandler(store, clock),
        bursts=BurstCoalescer(BURST_WINDOW_SECONDS),
    )
