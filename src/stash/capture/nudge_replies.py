from dataclasses import dataclass
from typing import assert_never

from stash.capture.digest_replies import render_digest
from stash.capture.nudge_buttons import action_rows
from stash.capture.occasions import emoji_of, occasion_of
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, Reply, telegram_length
from stash.capture.wording import LINE_LIMIT, counted, short_day
from stash.domain import KeyDateKind, collapse_and_clip
from stash.nudges.due import (
    DateReminder,
    DueNudge,
    FollowUp,
    PersonDateReminder,
    StepReminder,
    WeeklyDigest,
)
from stash.nudges.messages import NudgeMessage

CATCH_UP_HEADER = "While I was offline:"
STEP_LINE = "⏰ {text} — for {title}"
DATED_STEP_LINE = "⏰ {text} — for {title} ({day})"
DATE_LINE = "📅 {title} ({day})"
FOLLOW_UP_LINE = "How was {title}?"
PERSON_DATE_AHEAD_LINE = "{emoji} {occasion} in {lead} ({day})."
PERSON_DATE_TODAY_LINE = "{emoji} Today: {occasion}{age}."
AGE_SUFFIX = " (turns {age})"
GIFT_IDEAS_LINE = "Gift ideas: {ideas}"
GIFT_IDEA = "• {title}"
NO_GIFT_IDEAS_LINE = "No gift ideas saved yet."


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
        if kept and telegram_length(_text(candidate)) > TELEGRAM_TEXT_LIMIT:
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
        case PersonDateReminder():
            return _person_date_lines(due)
        case WeeklyDigest():
            return render_digest(due).text.splitlines()
        case _:
            assert_never(due)


def _step_line(reminder: StepReminder) -> str:
    text, title = reminder.step.text, reminder.item.title
    if reminder.item.date is None:
        return STEP_LINE.format(text=text, title=title)
    return DATED_STEP_LINE.format(text=text, title=title, day=short_day(reminder.item.date))


def _person_date_lines(reminder: PersonDateReminder) -> list[str]:
    occasion = occasion_of(reminder.person, reminder.key_date)
    emoji = emoji_of(reminder.key_date)
    if reminder.days_left == 0:
        age = _age_suffix(reminder)
        return [PERSON_DATE_TODAY_LINE.format(emoji=emoji, occasion=occasion, age=age)]
    ahead = PERSON_DATE_AHEAD_LINE.format(
        emoji=emoji,
        occasion=occasion,
        lead=counted(reminder.days_left, "day"),
        day=short_day(reminder.on),
    )
    return [ahead, _gift_ideas_line(reminder.gift_ideas)]


def _age_suffix(reminder: PersonDateReminder) -> str:
    years = reminder.key_date.years_on(reminder.on)
    if reminder.key_date.kind is not KeyDateKind.BIRTHDAY or years is None or years < 1:
        return ""
    return AGE_SUFFIX.format(age=years)


def _gift_ideas_line(ideas: tuple[str, ...]) -> str:
    if not ideas:
        return NO_GIFT_IDEAS_LINE
    return GIFT_IDEAS_LINE.format(ideas=" ".join(GIFT_IDEA.format(title=idea) for idea in ideas))
