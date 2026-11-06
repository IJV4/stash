from collections.abc import Mapping
from itertools import islice

from stash.domain import MAX_LEAD_DAYS, MIN_LEAD_DAYS, STEP_TEXT_LIMIT, printable_and_clip
from stash.planning.results import ProposedStep

MAX_PROPOSED_STEPS = 10


def parse_steps(raw: Mapping[str, object]) -> tuple[ProposedStep, ...]:
    entries = raw.get("steps")
    if not isinstance(entries, list):
        return ()
    proposed = (_proposed(entry) for entry in entries)
    usable = (step for step in proposed if step is not None)
    return tuple(islice(usable, MAX_PROPOSED_STEPS))


def _proposed(entry: object) -> ProposedStep | None:
    if not isinstance(entry, dict):
        return None
    text = _text(entry.get("text"))
    lead_days = _lead_days(entry.get("lead_days"))
    if text is None or lead_days is None:
        return None
    return ProposedStep(text, lead_days)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return printable_and_clip(value, STEP_TEXT_LIMIT) or None


def _lead_days(value: object) -> int | None:
    if type(value) is not int:
        return None
    return min(MAX_LEAD_DAYS, max(MIN_LEAD_DAYS, value))
