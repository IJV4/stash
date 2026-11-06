from collections.abc import Collection, Iterable, Iterator, Mapping
from itertools import islice

from stash.domain import SUGGESTION_REASON_LIMIT, printable_and_clip
from stash.suggestions.results import Suggestion


def parse_suggestions(
    raw: Mapping[str, object], allowed_ids: Collection[str], limit: int
) -> tuple[Suggestion, ...]:
    entries = raw.get("picks")
    if not isinstance(entries, list):
        return ()
    parsed = (_suggestion(entry, allowed_ids) for entry in entries)
    usable = (suggestion for suggestion in parsed if suggestion is not None)
    return tuple(islice(_first_of_each_item(usable), limit))


def _suggestion(entry: object, allowed_ids: Collection[str]) -> Suggestion | None:
    if not isinstance(entry, dict):
        return None
    item_id = entry.get("item_id")
    reason = _reason(entry.get("reason"))
    if not isinstance(item_id, str) or item_id not in allowed_ids or reason is None:
        return None
    return Suggestion(item_id, reason)


def _reason(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return printable_and_clip(value, SUGGESTION_REASON_LIMIT) or None


def _first_of_each_item(suggestions: Iterable[Suggestion]) -> Iterator[Suggestion]:
    seen: set[str] = set()
    for suggestion in suggestions:
        if suggestion.item_id not in seen:
            seen.add(suggestion.item_id)
            yield suggestion
