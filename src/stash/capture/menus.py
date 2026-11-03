from collections.abc import Sequence

from stash.capture.callbacks import FixAction, FixKind
from stash.capture.replies import Button, Reply
from stash.domain import Item, ItemType

TYPE_MENU_TEXT = "Pick a type:"
STAGE_MENU_TEXT = "Pick a stage:"
TYPE_ROW_WIDTH = 3
STAGE_ROW_WIDTH = 2


def type_menu(item: Item) -> Reply:
    buttons = [
        Button(item_type.label, FixAction(FixKind.SET_TYPE, item.id, item_type.value).encode())
        for item_type in ItemType
    ]
    return Reply(TYPE_MENU_TEXT, _rows(buttons, TYPE_ROW_WIDTH))


def stage_menu(item: Item) -> Reply:
    buttons = [
        Button(stage.label, FixAction(FixKind.SET_STAGE, item.id, stage.value).encode())
        for stage in item.moveable_stages()
    ]
    return Reply(STAGE_MENU_TEXT, _rows(buttons, STAGE_ROW_WIDTH))


def _rows(buttons: Sequence[Button], width: int) -> tuple[tuple[Button, ...], ...]:
    return tuple(tuple(buttons[start : start + width]) for start in range(0, len(buttons), width))
