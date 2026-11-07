import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import assert_never
from zoneinfo import ZoneInfo

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.callbacks import FixAction, FixKind
from stash.capture.completion_buttons import CompletionButtons
from stash.capture.menus import stage_menu, type_menu
from stash.capture.planning_buttons import PlanningButtons
from stash.capture.ports import FixStore, LifecycleActions, PlanningActions
from stash.capture.replies import Reply, busy, changed, confirmation, gone
from stash.capture.routing import QUESTION_PREFIX
from stash.domain import CaptureStatus, Item, ItemType, Stage, enum_member
from stash.store.port import StaleItemError, StoreBusyError, UnknownItemError

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
        store: FixStore,
        lifecycle: LifecycleActions,
        planning: PlanningActions,
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._store = store
        self._log = CallbackLog(logger)
        self._completion = CompletionButtons(store, lifecycle, self._log, clock, timezone)
        self._planning = PlanningButtons(store, planning, self._log)
        self._clock = clock
        self._lock = threading.Lock()

    def apply(self, data: str) -> Reply | Reroute:
        with self._lock:
            return self._apply(data)

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
        return self._replaced(item, item.retyped(item_type, self._clock()))

    def _move(self, item: Item, argument: str | None) -> Reply:
        stage = enum_member(Stage, argument)
        if stage is None:
            self._log.invalid(Subject.ITEM, item.id, Stage.__name__, argument)
            return stage_menu(item)
        if not item.can_move_to(stage):
            return stage_menu(item)
        return self._replaced(item, item.moved_to(stage, self._clock()))

    def _replaced(self, read: Item, updated: Item) -> Reply:
        try:
            self._store.update_item(updated, replacing=read)
        except UnknownItemError:
            self._log.unknown(Subject.ITEM, read.id)
            return gone()
        except StaleItemError:
            self._log.changed(Subject.ITEM, read.id)
            return changed()
        except StoreBusyError:
            self._log.busy()
            return busy()
        return confirmation(updated, unsure=False)

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
