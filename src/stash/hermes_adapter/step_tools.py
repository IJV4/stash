import logging

from stash.hermes_adapter.ports import StepPlanner
from stash.hermes_adapter.step_schemas import (
    ADD_STEP_SCHEMA,
    COMPLETE_STEP_SCHEMA,
    EDIT_STEP_SCHEMA,
)
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNWRITABLE, answering, step_answer
from stash.hermes_adapter.tool_spec import ToolSpec

logger = logging.getLogger(__name__)


class StepTools:
    def __init__(self, planner: StepPlanner) -> None:
        self._planner = planner

    def specs(self) -> tuple[ToolSpec, ...]:
        return (
            ToolSpec(ADD_STEP_SCHEMA, self.add_step),
            ToolSpec(EDIT_STEP_SCHEMA, self.edit_step),
            ToolSpec(COMPLETE_STEP_SCHEMA, self.complete_step),
        )

    def add_step(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._add_step, logger)

    def edit_step(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._edit_step, logger)

    def complete_step(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._complete_step, logger)

    def _add_step(self, arguments: ToolArguments) -> str:
        step = self._planner.add_step(
            arguments.required_id("item_id"),
            arguments.required_text("text"),
            lead_days=arguments.optional_lead_days(),
            due_on=arguments.optional_due_on(),
        )
        return step_answer(step)

    def _edit_step(self, arguments: ToolArguments) -> str:
        step = self._planner.edit_step(
            arguments.required_id("step_id"),
            text=arguments.nullable_text("text"),
            lead_days=arguments.optional_lead_days(),
            due_on=arguments.optional_due_on(),
        )
        return step_answer(step)

    def _complete_step(self, arguments: ToolArguments) -> str:
        return step_answer(self._planner.complete_step(arguments.required_id("step_id")))
