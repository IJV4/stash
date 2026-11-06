from dataclasses import dataclass

from builders import BASE, an_item
from capture_builders import a_pipeline, sequential_ids
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore
from fakes.recording_intake import RecordingIntake

from stash.capture import AgentCapture, Filed
from stash.capture.ports import AgentIntake


@dataclass(frozen=True, slots=True)
class AgentCaptureRig:
    store: MemoryStore
    filer: FakeCaptureFiler
    agent: AgentCapture


def an_agent_capture_over(intake: AgentIntake) -> AgentCapture:
    return AgentCapture(intake, sequential_ids(), lambda: BASE)


def build_agent_rig(filer: FakeCaptureFiler | None = None) -> AgentCaptureRig:
    store = MemoryStore()
    filer = filer or FakeCaptureFiler()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    return AgentCaptureRig(store, filer, an_agent_capture_over(pipeline))


def a_filing_intake() -> RecordingIntake:
    intake = RecordingIntake()
    intake.agent_result = Filed(an_item(), unsure=False)
    return intake
