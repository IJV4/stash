from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from builders import BASE
from fakes.scripted_chat_model import ScriptedChatModel
from fakes.store_factories import FreshStore
from nudge_builders import LONG_AGO, a_nudge_schedule, a_person_dates
from nudge_rig import NudgeRig, sending_nowhere
from suggestion_rig import an_engine

from stash.capture import Reply
from stash.delivery import NudgeDelivery
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
    store: FreshStore | None = None,
    model_outcomes: Sequence[dict[str, object] | LlmError] = (),
    send: Callable[[Reply], None] = sending_nowhere,
    *,
    first_run: bool = False,
) -> DigestRig:
    store = store or FreshStore()
    model = ScriptedChatModel(model_outcomes)
    schedule = a_nudge_schedule()
    builder = DigestBuilder(
        store, QuietPicks(SuggestionDesk(store, an_engine(model), lambda: BASE)), schedule
    )
    nudger = Nudger(store, schedule, a_person_dates(store, schedule))
    rig = DigestRig(
        store, schedule, nudger, send, NudgeDelivery(nudger, builder), model=model, builder=builder
    )
    if not first_run:
        FreshStore.record_all_sent(store, [WeeklyDigest(LONG_AGO, ()).nudge], LONG_AGO)
    return rig
