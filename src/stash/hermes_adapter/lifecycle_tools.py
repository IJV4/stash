import logging

from stash.domain import MOVEABLE_STAGES
from stash.hermes_adapter.lifecycle_schemas import (
    ANNOTATE_SCHEMA,
    COMPLETE_SCHEMA,
    GET_SCHEMA,
    GROUP_SCHEMA,
    KEEP_SCHEMA,
    LIBRARY_SCHEMA,
    SET_STAGE_SCHEMA,
)
from stash.hermes_adapter.ports import ItemLifecycle
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import (
    UNREADABLE,
    UNWRITABLE,
    answering,
    completion_answer,
    history_answer,
    item_answer,
    library_answer,
    outcome_answer,
)
from stash.hermes_adapter.tool_spec import ToolSpec
from stash.lifecycle import LibraryQuery

logger = logging.getLogger(__name__)

USE_STASH_COMPLETE = "use stash_complete to finish an item"


class LifecycleTools:
    def __init__(self, lifecycle: ItemLifecycle) -> None:
        self._lifecycle = lifecycle

    def specs(self) -> tuple[ToolSpec, ...]:
        return (
            ToolSpec(GET_SCHEMA, self.get),
            ToolSpec(COMPLETE_SCHEMA, self.complete),
            ToolSpec(ANNOTATE_SCHEMA, self.annotate),
            ToolSpec(SET_STAGE_SCHEMA, self.set_stage),
            ToolSpec(KEEP_SCHEMA, self.keep),
            ToolSpec(GROUP_SCHEMA, self.group),
            ToolSpec(LIBRARY_SCHEMA, self.library),
        )

    def get(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._get, logger)

    def complete(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._complete, logger)

    def annotate(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._annotate, logger)

    def set_stage(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._set_stage, logger)

    def keep(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._keep, logger)

    def group(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._group, logger)

    def library(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._library, logger)

    def _get(self, arguments: ToolArguments) -> str:
        return history_answer(self._lifecycle.history(arguments.required_id("item_id")))

    def _complete(self, arguments: ToolArguments) -> str:
        completion = self._lifecycle.complete(
            arguments.required_id("item_id"),
            rating=arguments.optional_rating(),
            notes=arguments.optional_text("notes"),
            takeaways=arguments.optional_takeaways() or (),
            keep=arguments.optional_bool("keep"),
            on=arguments.optional_date("completed_on"),
        )
        return completion_answer(completion)

    def _annotate(self, arguments: ToolArguments) -> str:
        outcome = self._lifecycle.annotate(
            arguments.required_id("outcome_id"),
            notes=arguments.nullable_text("notes"),
            takeaways=arguments.optional_takeaways(),
            rating=arguments.optional_rating(),
        )
        return outcome_answer(outcome)

    def _set_stage(self, arguments: ToolArguments) -> str:
        item_id = arguments.required_id("item_id")
        stage = arguments.stage()
        if stage not in MOVEABLE_STAGES:
            raise ValueError(USE_STASH_COMPLETE)
        return item_answer(self._lifecycle.set_stage(item_id, stage, arguments.optional_reason()))

    def _keep(self, arguments: ToolArguments) -> str:
        kept = self._lifecycle.keep(
            arguments.required_id("item_id"), arguments.required_bool("kept")
        )
        return item_answer(kept)

    def _group(self, arguments: ToolArguments) -> str:
        child_id = arguments.required_id("child_id")
        parent_id = arguments.nullable_id("parent_id")
        if parent_id is None:
            return item_answer(self._lifecycle.ungroup(child_id))
        return item_answer(self._lifecycle.group(child_id, parent_id))

    def _library(self, arguments: ToolArguments) -> str:
        query = LibraryQuery(arguments.optional_item_type(), arguments.limit())
        return library_answer(self._lifecycle.library(query))
