import datetime as dt
from collections.abc import Sequence
from enum import StrEnum
from typing import assert_never

from stash.nudges.due import DateReminder, DueNudge, FollowUp, StepReminder, WeeklyDigest
from stash.nudges.messages import NudgeMessage

CATCH_UP_AFTER = dt.timedelta(minutes=30)


class _Group(StrEnum):
    REMINDERS = "reminders"
    FOLLOW_UPS = "follow_ups"
    DIGEST = "digest"


def batch_messages(due: Sequence[DueNudge], now: dt.datetime) -> tuple[NudgeMessage, ...]:
    groups = tuple(tuple(nudge for nudge in due if _group_of(nudge) is group) for group in _Group)
    messages = tuple(NudgeMessage(group, catch_up=False) for group in groups if group)
    if len(messages) > 1 and _oldest(due) < now - CATCH_UP_AFTER:
        return (NudgeMessage(tuple(nudge for group in groups for nudge in group), catch_up=True),)
    return messages


def _group_of(nudge: DueNudge) -> _Group:
    match nudge:
        case StepReminder() | DateReminder():
            return _Group.REMINDERS
        case FollowUp():
            return _Group.FOLLOW_UPS
        case WeeklyDigest():
            return _Group.DIGEST
        case _:
            assert_never(nudge)


def _oldest(due: Sequence[DueNudge]) -> dt.datetime:
    return min(nudge.due_at for nudge in due)
