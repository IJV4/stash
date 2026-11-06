import logging
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from stash.config import LlmTask
from stash.domain import Item, require_aware
from stash.llm import LlmBadOutput
from stash.planning.parse import parse_steps
from stash.planning.ports import PlanningModelSource
from stash.planning.prompt import build_step_messages
from stash.planning.results import ProposedStep
from stash.planning.schema import SCHEMA_NAME, STEPS_SCHEMA

logger = logging.getLogger(__name__)


class StepProposer:
    def __init__(
        self,
        models: PlanningModelSource,
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
        try:
            answer = model.complete_json(messages, STEPS_SCHEMA, SCHEMA_NAME)
        except LlmBadOutput as error:
            logger.warning("step model gave unusable output: %s", type(error).__name__)
            return ()
        return parse_steps(answer)
