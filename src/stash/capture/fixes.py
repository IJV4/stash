import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import assert_never
from zoneinfo import ZoneInfo

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.callbacks import FixAction, FixKind
from stash.capture.completion_buttons import CompletionButtons, answering
from stash.capture.menus import stage_menu, type_menu
from stash.capture.planning_buttons import PlanningButtons
from stash.capture.ports import LifecycleActions, PlanningActions
from stash.capture.replies import Reply, busy, confirmation, gone
from stash.capture.routing import QUESTION_PREFIX
from stash.domain import CaptureStatus, Item, ItemType, Stage, enum_member
from stash.store.port import Store, StoreBusyError

logger = logging.getLogger(__name__)

HISTORY_KEPT = (
    "That item has a history now, so I kept it — "
    f"send the question again starting with {QUESTION_PREFIX} to ask."
)


@dataclass(frozen=True, slots=True)
class Reroute:
    text: str


class FixHandler:
    def __init__(
        self,
        store: Store,
        lifecycle: LifecycleActions,
        planning: PlanningActions,
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._store = store
        self._lifecycle = lifecycle
        self._log = CallbackLog(logger)
        self._completion = CompletionButtons(store, lifecycle, self._log, clock, timezone)
        self._planning = PlanningButtons(store, planning, self._log)

    def apply(self, data: str) -> Reply | Reroute:
        try:
            with self._store.writing():
                return self._apply(data)
        except StoreBusyError:
            self._log.busy()
            return busy()

    def _apply(self, data: str) -> Reply | Reroute:
        action = FixAction.parse(data)
        if action is None:
            self._log.unparseable(data)
            return gone()
        match action.kind:
            case FixKind.QUESTION:
                return self._question(action.subject_id)
            case FixKind.TYPE_MENU:
                return self._for_item(action.subject_id, type_menu)
            case FixKind.STAGE_MENU:
                return self._for_item(action.subject_id, stage_menu)
            case FixKind.SET_TYPE:
                return self._for_item(
                    action.subject_id, lambda item: self._retype(item, action.argument)
                )
            case FixKind.SET_STAGE:
                return self._for_item(
                    action.subject_id, lambda item: self._move(item, action.argument)
                )
            case FixKind.DONE:
                return self._completion.done(action.subject_id)
            case FixKind.RATE:
                return self._completion.rate(action.subject_id, action.argument)
            case FixKind.KEEP:
                return self._completion.keep(action.subject_id, action.argument)
            case FixKind.ACCEPT_STEPS:
                return self._planning.accept(action.subject_id)
            case FixKind.SKIP_STEPS:
                return self._planning.skip(action.subject_id)
            case FixKind.STEP_DONE:
                return self._planning.step_done(action.subject_id)
            case FixKind.NOT_HAPPENED:
                return self._completion.didnt_happen(action.subject_id, action.argument)
            case _:
                assert_never(action.kind)

    def _for_item(self, item_id: str, handle: Callable[[Item], Reply]) -> Reply:
        item = self._store.get_item(item_id)
        if item is None:
            self._log.unknown(Subject.ITEM, item_id)
            return gone()
        return handle(item)

    def _retype(self, item: Item, argument: str | None) -> Reply:
        item_type = enum_member(ItemType, argument)
        if item_type is None:
            self._log.invalid(Subject.ITEM, item.id, ItemType.__name__, argument)
            return gone()
        return self._confirming(partial(self._lifecycle.retype, item.id, item_type))

    def _move(self, item: Item, argument: str | None) -> Reply:
        stage = enum_member(Stage, argument)
        if stage is None:
            self._log.invalid(Subject.ITEM, item.id, Stage.__name__, argument)
            return stage_menu(item)
        if not item.can_move_to(stage):
            return stage_menu(item)
        reason = item.drop_reason if stage is Stage.DROPPED else None
        return self._confirming(partial(self._lifecycle.set_stage, item.id, stage, reason))

    def _confirming(self, change: Callable[[], Item]) -> Reply:
        return answering(lambda: confirmation(change(), unsure=False), self._log)

    def _question(self, capture_id: str) -> Reply | Reroute:
        capture = self._store.get_capture(capture_id)
        if capture is None or self._store.get_item(capture.item_id) is None:
            self._log.unknown(Subject.CAPTURE, capture_id)
            return gone()
        self._store.set_capture_status(capture.id, CaptureStatus.REQUEST)
        if not self._store.delete_item_if_untouched(capture.item_id):
            self._store.set_capture_status(capture.id, capture.status)
            return Reply(HISTORY_KEPT)
        logger.info("capture %s rerouted as a question", capture.id)
        return Reroute(capture.text)
