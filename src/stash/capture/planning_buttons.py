from collections.abc import Callable
from functools import partial

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.planning_replies import step_done_reply, steps_saved_reply, steps_skipped_reply
from stash.capture.ports import ItemLookup, PlanningActions
from stash.capture.replies import Reply, gone, refused
from stash.domain import Item
from stash.planning.errors import PlanningRefused, UnknownItem, UnknownStep


class PlanningButtons:
    def __init__(
        self, items: ItemLookup, planning: PlanningActions, callback_log: CallbackLog
    ) -> None:
        self._items = items
        self._planning = planning
        self._log = callback_log

    def accept(self, item_id: str) -> Reply:
        return self._answering(partial(self._accepted, item_id))

    def skip(self, item_id: str) -> Reply:
        return self._answering(partial(self._skipped, item_id))

    def step_done(self, step_id: str) -> Reply:
        return self._answering(partial(self._completed, step_id))

    def _accepted(self, item_id: str) -> Reply:
        steps = self._planning.confirm_all(item_id)
        return self._titled(item_id, lambda item: steps_saved_reply(item, steps))

    def _skipped(self, item_id: str) -> Reply:
        self._planning.discard(item_id)
        return self._titled(item_id, steps_skipped_reply)

    def _completed(self, step_id: str) -> Reply:
        return step_done_reply(self._planning.complete_step(step_id))

    def _titled(self, item_id: str, reply_for: Callable[[Item], Reply]) -> Reply:
        item = self._items.get_item(item_id)
        if item is None:
            self._log.unknown(Subject.ITEM, item_id)
            return gone()
        return reply_for(item)

    def _answering(self, build_reply: Callable[[], Reply]) -> Reply:
        try:
            return build_reply()
        except UnknownItem as error:
            self._log.unknown(Subject.ITEM, error.item_id)
            return gone()
        except UnknownStep as error:
            self._log.unknown(Subject.STEP, error.step_id)
            return gone()
        except PlanningRefused as error:
            return refused(str(error))
