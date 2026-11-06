from typing import Any

from builders import BASE

from stash.domain import Nudge, NudgeKind, Step

DUE_AT = BASE.replace(hour=9)


def a_step(**overrides: Any) -> Step:
    fields: dict[str, Any] = {
        "id": "s1",
        "item_id": "i1",
        "text": "Book the table",
        "lead_days": 7,
        "due_on": None,
        "confirmed": False,
        "done": False,
        "position": 0,
        "created_at": BASE,
    }
    return Step(**{**fields, **overrides})


def a_nudge(**overrides: Any) -> Nudge:
    fields: dict[str, Any] = {
        "kind": NudgeKind.STEP,
        "subject_id": "s1",
        "due_at": DUE_AT,
        "title": "Book the table",
    }
    return Nudge(**{**fields, **overrides})
