from datetime import UTC, datetime
from typing import Any

from backup_builders import a_backups
from builders import a_capture, a_source
from capture_builders import sequential_ids
from config_builders import a_stash_config
from fakes.backup_source import FakeBackupSource
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from fakes.close_counter import CloseCounter
from fakes.fake_suggestion_picker import FakeSuggestionPicker
from fakes.ocr import FakeOcr
from fakes.pending_intake import PendingIntake
from fakes.recording_unloader import RecordingUnloader
from fakes.store_factories import FreshStore
from gate_rig import a_gate, a_sample
from lifecycle_rig import LOCAL_ZONE, a_lifecycle
from nudge_builders import a_nudge_schedule, a_person_dates
from people_builders import a_directory
from planning_rig import a_planning
from router_builders import default_thinking_models

from stash.app import StashApp
from stash.capture import AgentCapture, BurstCoalescer, FixHandler
from stash.config import ProviderName, Thinking
from stash.delivery import NudgeDelivery, ProposalDelivery
from stash.doctor import Doctor
from stash.domain import Item
from stash.evaluation import EvalTargets
from stash.gpu_switch import GpuSwitch
from stash.llm import ModelRouter
from stash.nudges import DigestBuilder, Nudger
from stash.suggestions import QuietPicks, SuggestionDesk

NOON = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def stored(*items: Item) -> FreshStore:
    store = FreshStore()
    for item in items:
        store.add_capture(a_capture(id=item.capture_id, source=a_source(item.capture_id)))
        store.save_item(item)
    return store


def an_app(**overrides: Any) -> StashApp:
    config = a_stash_config()
    store = overrides.get("store", FreshStore())
    clock = overrides.get("clock", lambda: NOON)
    lifecycle = overrides.get("lifecycle", a_lifecycle(store, clock))
    gate = a_gate(a_sample(), store=store)
    planning = overrides.get("planning", a_planning(store, FakeChatModel(), clock))
    pipeline = overrides.get("pipeline", PendingIntake())
    suggestions = overrides.get("suggestions", SuggestionDesk(store, FakeSuggestionPicker()))
    schedule = a_nudge_schedule()
    fields: dict[str, Any] = {
        "config": config,
        "store": store,
        "pipeline": pipeline,
        "agent_capture": AgentCapture(pipeline, sequential_ids(), clock),
        "fixes": FixHandler(store, lifecycle, planning, clock, LOCAL_ZONE),
        "lifecycle": lifecycle,
        "planning": planning,
        "people": a_directory(store),
        "suggestions": suggestions,
        "nudge_delivery": NudgeDelivery(
            Nudger(store, schedule, a_person_dates(store, schedule)),
            DigestBuilder(store, QuietPicks(suggestions), schedule),
        ),
        "proposal_delivery": ProposalDelivery(planning, store),
        "gpu": gate,
        "gpu_switch": GpuSwitch(gate, RecordingUnloader()),
        "router": ModelRouter(
            config.llm,
            default_thinking_models({ProviderName.OLLAMA: FakeChatModel()}),
            FakeBusy(),
        ),
        "doctor": Doctor([]),
        "burst_factory": lambda: BurstCoalescer(config.burst_window_seconds),
        "clock": clock,
        "eval_targets": EvalTargets((), Thinking.DEFAULT),
        "ocr": FakeOcr(),
        "backups": a_backups(FakeBackupSource()),
        "resources": CloseCounter(),
    }
    return StashApp(**{**fields, **overrides})
