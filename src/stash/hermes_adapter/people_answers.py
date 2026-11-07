from collections.abc import Iterable
from typing import Any

from stash.domain import KeyDate, NextKeyDate, Person, PersonSummary
from stash.hermes_adapter.tool_json import dump


def _person_payload(person: Person) -> dict[str, Any]:
    return {
        "id": person.id,
        "name": person.name,
        "relation": person.relation,
        "aliases": list(person.aliases),
    }


def _key_date_payload(key_date: KeyDate) -> dict[str, Any]:
    return {
        "id": key_date.id,
        "person_id": key_date.person_id,
        "kind": key_date.kind.value,
        "label": key_date.label,
        "month": key_date.month,
        "day": key_date.day,
        "year": key_date.year,
    }


def _next_payload(next_date: NextKeyDate | None) -> dict[str, Any] | None:
    if next_date is None:
        return None
    key_date = next_date.key_date
    return {"kind": key_date.kind.value, "label": key_date.label, "on": next_date.on.isoformat()}


def people_answer(summaries: Iterable[PersonSummary]) -> str:
    return dump(
        {
            "people": [
                {
                    **_person_payload(summary.person),
                    "next_key_date": _next_payload(summary.next_date),
                }
                for summary in summaries
            ]
        }
    )


def person_answer(person: Person) -> str:
    return dump({"person": _person_payload(person)})


def key_date_answer(key_date: KeyDate) -> str:
    return dump({"key_date": _key_date_payload(key_date)})


def linked_answer(item_id: str, person_id: str) -> str:
    return dump({"linked": {"item_id": item_id, "person_id": person_id}})


def removed_answer(person_id: str) -> str:
    return dump({"removed": person_id})
