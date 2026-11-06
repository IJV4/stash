from dataclasses import dataclass
from typing import assert_never

from stash.capture.digest_replies import render_digest
from stash.capture.nudge_buttons import action_rows
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, Reply
from stash.capture.wording import LINE_LIMIT, short_day
from stash.domain import collapse_and_clip
from stash.nudges.due import DateReminder, DueNudge, FollowUp, StepReminder, WeeklyDigest
from stash.nudges.messages import NudgeMessage

CATCH_UP_HEADER = "While I was offline:"
STEP_LINE = "⏰ {text} — for {title}"
DATED_STEP_LINE = "⏰ {text} — for {title} ({day})"
DATE_LINE = "📅 {title} ({day})"
FOLLOW_UP_LINE = "How was {title}?"


@dataclass(frozen=True, slots=True)
class NudgeReply:
    reply: Reply
    shown: NudgeMessage


def nudge_reply(message: NudgeMessage) -> NudgeReply:
    shown = _fitting(message)
    return NudgeReply(Reply(_text(shown), action_rows(shown.due)), shown)


def _fitting(message: NudgeMessage) -> NudgeMessage:
    kept: list[DueNudge] = []
    for due in message.due:
        candidate = NudgeMessage((*kept, due), message.catch_up)
        if kept and len(_text(candidate)) > TELEGRAM_TEXT_LIMIT:
            break
        kept.append(due)
    return NudgeMessage(tuple(kept), message.catch_up)


def _text(message: NudgeMessage) -> str:
    lines = [line for due in message.due for line in _lines(due)]
    if message.catch_up:
        lines.insert(0, CATCH_UP_HEADER)
    return "\n".join(collapse_and_clip(line, LINE_LIMIT) for line in lines)


def _lines(due: DueNudge) -> list[str]:
    match due:
        case StepReminder():
            return [_step_line(due)]
        case DateReminder():
            return [DATE_LINE.format(title=due.item.title, day=short_day(due.on))]
        case FollowUp():
            return [FOLLOW_UP_LINE.format(title=due.item.title)]
        case WeeklyDigest():
            return render_digest(due).text.splitlines()
        case _:
            assert_never(due)


def _step_line(reminder: StepReminder) -> str:
    text, title = reminder.step.text, reminder.item.title
    if reminder.item.date is None:
        return STEP_LINE.format(text=text, title=title)
    return DATED_STEP_LINE.format(text=text, title=title, day=short_day(reminder.item.date))
