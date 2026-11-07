from dataclasses import dataclass
from typing import assert_never

from stash.domain import Nudge
from stash.nudges.due import (
    DateReminder,
    DueNudge,
    FollowUp,
    PersonDateReminder,
    StepReminder,
    WeeklyDigest,
)


@dataclass(frozen=True, slots=True)
class NudgeMessage:
    due: tuple[DueNudge, ...]
    catch_up: bool

    def __post_init__(self) -> None:
        if not self.due:
            raise ValueError("a message carries at least one nudge")

    @property
    def nudges(self) -> tuple[Nudge, ...]:
        return tuple(nudge for due in self.due for nudge in _nudges_of(due))


def _nudges_of(due: DueNudge) -> tuple[Nudge, ...]:
    match due:
        case StepReminder() | DateReminder() | FollowUp() | PersonDateReminder():
            return (due.nudge,)
        case WeeklyDigest():
            return due.nudges
        case _:
            assert_never(due)
