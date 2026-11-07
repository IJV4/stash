from collections.abc import Iterable
from typing import assert_never

from stash.capture.callbacks import FixAction, FixKind, date_argument
from stash.capture.replies import DONE_LABEL, Button
from stash.domain import Item, collapse_and_clip
from stash.nudges.due import DueNudge, FollowUp, StepReminder

MAX_BUTTONS = 8
SUBJECT_LIMIT = 24
NAMED_DONE_LABEL = "{done} · {subject}"
DIDNT_HAPPEN_LABEL = "Didn't happen"

Row = tuple[Button, ...]


def action_rows(due: Iterable[DueNudge]) -> tuple[Row, ...]:
    actionable = [nudge for nudge in due if isinstance(nudge, StepReminder | FollowUp)]
    names_subject = len(actionable) > 1
    return _rows_until_the_first_that_does_not_fit(
        [_row(nudge, names_subject) for nudge in actionable]
    )


def _row(nudge: StepReminder | FollowUp, names_subject: bool) -> Row:
    match nudge:
        case StepReminder():
            done = FixAction(FixKind.STEP_DONE, nudge.step.id)
            return (_done_button(nudge.step.text if names_subject else None, done),)
        case FollowUp():
            done = FixAction(FixKind.DONE, nudge.item.id)
            return (
                _done_button(nudge.item.title if names_subject else None, done),
                *_didnt_happen_button(nudge.item),
            )
        case _:
            assert_never(nudge)


def _didnt_happen_button(item: Item) -> Row:
    if item.date is None:
        return ()
    action = FixAction(FixKind.NOT_HAPPENED, item.id, date_argument(item.date))
    return (Button(DIDNT_HAPPEN_LABEL, action.encode()),)


def _done_button(subject: str | None, action: FixAction) -> Button:
    if subject is None:
        return Button(DONE_LABEL, action.encode())
    clipped = collapse_and_clip(subject, SUBJECT_LIMIT)
    return Button(NAMED_DONE_LABEL.format(done=DONE_LABEL, subject=clipped), action.encode())


def _rows_until_the_first_that_does_not_fit(rows: list[Row]) -> tuple[Row, ...]:
    kept: list[Row] = []
    used = 0
    for row in rows:
        used += len(row)
        if used > MAX_BUTTONS:
            break
        kept.append(row)
    return tuple(kept)
