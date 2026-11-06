from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from fakes.memory_store import MemoryStore
from fakes.scripted_chat_model import ScriptedChatModel
from nudge_builders import a_nudge_schedule
from nudge_rig import NudgeRig, sending_nowhere
from suggestion_rig import an_engine

from stash.capture import Reply
from stash.llm import LlmError
from stash.nudges import DueNudge, Nudger, WeeklyDigest
from stash.nudges.digest_builder import DigestBuilder
from stash.suggestions import QuietPicks, SuggestionDesk


@dataclass(slots=True)
class DigestRig(NudgeRig):
    model: ScriptedChatModel = field(kw_only=True)
    builder: DigestBuilder = field(kw_only=True)

    def due(self, now: datetime) -> list[DueNudge]:
        return [
            self.builder.build(due, now) if isinstance(due, WeeklyDigest) else due
            for due in self.nudger.due(now)
        ]


def a_digest_rig(
    store: MemoryStore | None = None,
    model_outcomes: Sequence[dict[str, object] | LlmError] = (),
    send: Callable[[Reply], None] = sending_nowhere,
) -> DigestRig:
    store = store or MemoryStore()
    model = ScriptedChatModel(model_outcomes)
    schedule = a_nudge_schedule()
    builder = DigestBuilder(store, QuietPicks(SuggestionDesk(store, an_engine(model))), schedule)
    return DigestRig(store, schedule, Nudger(store, schedule), send, model=model, builder=builder)
