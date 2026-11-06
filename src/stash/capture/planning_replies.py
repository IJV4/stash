from collections.abc import Sequence
from datetime import date

from stash.capture.callbacks import FixAction, FixKind
from stash.capture.replies import Button, Reply
from stash.domain import Item, Step
from stash.planning.results import Proposal

HEADER_TEXT = "🗓 Prep for {title} ({day}):"
STEP_LINE = "• {text} — {when}"
CHANGES_FOOTER = "Tell me changes any time."
SAME_DAY = "same day"
DAYS_BEFORE = "{days} before"
SAVED_TEXT = "✅ Prep saved for {title}: {steps}. I'll remind you when each is due."
NO_PROPOSED_STEPS_TEXT = "There are no proposed steps for {title} any more."
NOTHING_TO_PREP_TEXT = "🗓 Nothing to prep for {title} ({day})."
SKIPPED_TEXT = "Okay, I dropped the proposed steps for {title}."
STEP_DONE_TEXT = "✅ Done: {text}"
ACCEPT_LABEL = "Looks good ✓"
SKIP_LABEL = "No steps"


def proposal_reply(proposal: Proposal, item_date: date) -> Reply:
    item = proposal.item
    if not proposal.steps:
        return Reply(NOTHING_TO_PREP_TEXT.format(title=item.title, day=_day(item_date)))
    lines = [
        HEADER_TEXT.format(title=item.title, day=_day(item_date)),
        *(STEP_LINE.format(text=step.text, when=_when(step)) for step in proposal.steps),
        CHANGES_FOOTER,
    ]
    return Reply("\n".join(lines), (_choice_row(item),))


def steps_saved_reply(item: Item, steps: Sequence[Step]) -> Reply:
    if not steps:
        return Reply(NO_PROPOSED_STEPS_TEXT.format(title=item.title))
    return Reply(SAVED_TEXT.format(title=item.title, steps=_counted(len(steps), "step")))


def steps_skipped_reply(item: Item) -> Reply:
    return Reply(SKIPPED_TEXT.format(title=item.title))


def step_done_reply(step: Step) -> Reply:
    return Reply(STEP_DONE_TEXT.format(text=step.text))


def _choice_row(item: Item) -> tuple[Button, ...]:
    return (
        Button(ACCEPT_LABEL, FixAction(FixKind.ACCEPT_STEPS, item.id).encode()),
        Button(SKIP_LABEL, FixAction(FixKind.SKIP_STEPS, item.id).encode()),
    )


def _day(day: date) -> str:
    return f"{day:%a %b} {day.day}"


def _when(step: Step) -> str:
    if step.due_on is not None:
        return _day(step.due_on)
    if not step.lead_days:
        return SAME_DAY
    return DAYS_BEFORE.format(days=_counted(step.lead_days, "day"))


def _counted(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
