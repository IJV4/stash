import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import assert_never

from stash.capture.callbacks import FixAction, FixKind
from stash.capture.menus import stage_menu, type_menu
from stash.capture.ports import FixStore
from stash.capture.replies import Reply, confirmation, gone
from stash.domain import CaptureStatus, Item, ItemType, Stage, enum_member

logger = logging.getLogger(__name__)

MAX_LOGGED_CALLBACK_CHARS = 64


@dataclass(frozen=True, slots=True)
class Reroute:
    text: str


class FixHandler:
    def __init__(self, store: FixStore, clock: Callable[[], datetime]) -> None:
        self._store = store
        self._clock = clock

    def apply(self, data: str) -> Reply | Reroute:
        action = FixAction.parse(data)
        if action is None:
            logger.warning("unparseable fix callback: %r", _logged(data))
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
            case _:
                assert_never(action.kind)

    def _for_item(self, item_id: str, handle: Callable[[Item], Reply]) -> Reply:
        item = self._store.get_item(item_id)
        if item is None:
            logger.info("fix callback for unknown item %s", _logged(item_id))
            return gone()
        return handle(item)

    def _retype(self, item: Item, argument: str | None) -> Reply:
        item_type = enum_member(ItemType, argument)
        if item_type is None:
            _log_invalid(item, ItemType, argument)
            return gone()
        updated = item.retyped(item_type, self._clock())
        self._store.save_item(updated)
        return confirmation(updated, unsure=False)

    def _move(self, item: Item, argument: str | None) -> Reply:
        stage = enum_member(Stage, argument)
        if stage is None:
            _log_invalid(item, Stage, argument)
            return stage_menu(item)
        if not item.can_move_to(stage):
            return stage_menu(item)
        updated = item.moved_to(stage, self._clock())
        self._store.save_item(updated)
        return confirmation(updated, unsure=False)

    def _question(self, capture_id: str) -> Reply | Reroute:
        capture = self._store.get_capture(capture_id)
        if capture is None or self._store.get_item(capture.item_id) is None:
            logger.info("fix callback for unknown capture %s", _logged(capture_id))
            return gone()
        self._store.set_capture_status(capture.id, CaptureStatus.REQUEST)
        self._store.delete_item(capture.item_id)
        logger.info("capture %s rerouted as a question", capture.id)
        return Reroute(capture.text)


def _logged(value: str | None) -> str | None:
    return None if value is None else value[:MAX_LOGGED_CALLBACK_CHARS]


def _log_invalid(item: Item, kind: type[StrEnum], value: str | None) -> None:
    logger.warning(
        "fix callback for item %s has an invalid %s %r", item.id, kind.__name__, _logged(value)
    )
