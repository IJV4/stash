import json
import logging
from collections.abc import Callable, Iterable
from typing import Any

from stash.capture import Deferred, Filed
from stash.domain import Item, Outcome, Step
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.lifecycle import Completion, ItemHistory, LibraryEntry, LifecycleError
from stash.planning.errors import PlanningError

UNREADABLE = "the stash could not be read"
UNWRITABLE = "the stash could not be updated"

Work = Callable[[ToolArguments], str]


def dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def error(message: str) -> str:
    return dump({"error": message})


def answering(args: object, failure: str, work: Work, log: logging.Logger) -> str:
    try:
        return work(ToolArguments.of(args))
    except (ValueError, LifecycleError, PlanningError) as refusal:
        return error(str(refusal))
    except Exception:
        log.exception("a stash tool failed")
        return error(failure)


def item_entry(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "type": item.item_type.value,
        "title": item.title,
        "stage": item.stage.value,
        "date": None if item.date is None else item.date.isoformat(),
    }


def item_payload(item: Item) -> dict[str, Any]:
    return {
        **item_entry(item),
        "kept": item.kept,
        "in_library": item.in_library,
        "parent_id": item.parent_id,
        "drop_reason": item.drop_reason,
        "source_url": item.source_url,
        "note": item.note,
        "details": dict(item.details),
    }


def outcome_payload(outcome: Outcome) -> dict[str, Any]:
    return {
        "id": outcome.id,
        "completed_on": outcome.completed_on.isoformat(),
        "rating": outcome.rating,
        "notes": outcome.notes,
        "takeaways": list(outcome.takeaways),
    }


def library_entry(entry: LibraryEntry) -> dict[str, Any]:
    completed_on = entry.completed_on
    return {
        **item_entry(entry.item),
        "rating": entry.rating,
        "completed_on": None if completed_on is None else completed_on.isoformat(),
    }


def items_answer(items: Iterable[Item]) -> str:
    return dump({"items": [item_entry(item) for item in items]})


def library_answer(entries: Iterable[LibraryEntry]) -> str:
    return dump({"items": [library_entry(entry) for entry in entries]})


def history_answer(history: ItemHistory) -> str:
    return dump(
        {
            "item": item_payload(history.item),
            "outcomes": [outcome_payload(outcome) for outcome in history.outcomes],
            "children": [item_entry(child) for child in history.children],
        }
    )


def completion_answer(completion: Completion) -> str:
    return dump(
        {
            "item": item_payload(completion.item),
            "outcome": outcome_payload(completion.outcome),
            "repeat": completion.repeat,
        }
    )


def item_answer(item: Item) -> str:
    return dump({"item": item_payload(item)})


def outcome_answer(outcome: Outcome) -> str:
    return dump({"outcome": outcome_payload(outcome)})


def step_payload(step: Step) -> dict[str, Any]:
    return {
        "id": step.id,
        "item_id": step.item_id,
        "text": step.text,
        "lead_days": step.lead_days,
        "due_on": None if step.due_on is None else step.due_on.isoformat(),
        "confirmed": step.confirmed,
        "done": step.done,
        "position": step.position,
    }


def step_answer(step: Step) -> str:
    return dump({"step": step_payload(step)})


def capture_answer(result: Filed | Deferred) -> str:
    if isinstance(result, Deferred):
        return dump({"saved": True, "pending": True})
    item = result.item
    return dump(
        {
            "item_id": item.id,
            "title": item.title,
            "item_type": item.item_type.value,
            "stage": item.stage.value,
        }
    )
