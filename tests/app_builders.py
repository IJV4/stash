from datetime import UTC, datetime
from typing import Any

from builders import a_capture, a_source
from capture_rig import a_fix_handler
from config_builders import a_stash_config
from fakes.backup_source import FakeBackupSource
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from fakes.close_counter import CloseCounter
from fakes.memory_store import MemoryStore
from fakes.ocr import FakeOcr
from fakes.pending_intake import PendingIntake
from fakes.recording_unloader import RecordingUnloader
from gate_rig import a_gate, a_sample
from router_builders import default_thinking_models

from stash.app import StashApp
from stash.capture import BurstCoalescer
from stash.config import ProviderName, Thinking
from stash.doctor import Doctor
from stash.domain import Item
from stash.evaluation import EvalTargets
from stash.gpu_switch import GpuSwitch
from stash.llm import ModelRouter
from stash.store.backup import Backups

NOON = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def stored(*items: Item) -> MemoryStore:
    store = MemoryStore()
    for item in items:
        store.add_capture(a_capture(id=item.capture_id, source=a_source(item.capture_id)))
        store.save_item(item)
    return store


def an_app(**overrides: Any) -> StashApp:
    config = a_stash_config()
    store = MemoryStore()
    gate = a_gate(a_sample(), store=store)
    fields: dict[str, Any] = {
        "config": config,
        "store": store,
        "pipeline": PendingIntake(),
        "fixes": a_fix_handler(store, lambda: NOON),
        "gpu": gate,
        "gpu_switch": GpuSwitch(gate, RecordingUnloader()),
        "router": ModelRouter(
            config.llm,
            default_thinking_models({ProviderName.OLLAMA: FakeChatModel()}),
            FakeBusy(),
        ),
        "doctor": Doctor([]),
        "burst_factory": lambda: BurstCoalescer(config.burst_window_seconds),
        "clock": lambda: NOON,
        "eval_targets": EvalTargets((), Thinking.DEFAULT),
        "ocr": FakeOcr(),
        "backups": Backups(FakeBackupSource()),
        "resources": CloseCounter(),
    }
    return StashApp(**{**fields, **overrides})
