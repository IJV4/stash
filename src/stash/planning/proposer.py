from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from stash.config import LlmTask
from stash.domain import Item, require_aware
from stash.llm import ModelSource
from stash.planning.parse import parse_steps
from stash.planning.prompt import build_step_messages
from stash.planning.results import ProposedStep
from stash.planning.schema import SCHEMA_NAME, STEPS_SCHEMA


class StepProposer:
    def __init__(
        self,
        models: ModelSource,
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._models = models
        self._clock = clock
        self._timezone = timezone

    def propose(self, item: Item) -> tuple[ProposedStep, ...]:
        now = self._clock()
        require_aware("clock", now)
        model = self._models.model_for(LlmTask.SUGGESTIONS, now)
        messages = build_step_messages(item, now.astimezone(self._timezone).date())
        answer = model.complete_json(messages, STEPS_SCHEMA, SCHEMA_NAME)
        return parse_steps(answer)
