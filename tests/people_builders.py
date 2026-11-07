from datetime import date
from typing import Any

from builders import BASE, an_item, in_los_angeles, stored
from capture_builders import sequential_ids
from fakes.memory_store import MemoryStore

from stash.domain import ItemType, KeyDate, KeyDateKind, Person, Stage
from stash.nudges import PersonDateReminder
from stash.people import PeopleDirectory
from stash.store import Store


def a_person(**overrides: Any) -> Person:
    fields: dict[str, Any] = {
        "id": "p1",
        "name": "Ana Rivera",
        "relation": "sister",
        "aliases": ("Anita",),
        "notes": "Loves ceramics",
        "created_at": BASE,
    }
    return Person(**{**fields, **overrides})


def a_key_date(**overrides: Any) -> KeyDate:
    fields: dict[str, Any] = {
        "id": "k1",
        "person_id": "p1",
        "kind": KeyDateKind.BIRTHDAY,
        "label": "Birthday",
        "month": 3,
        "day": 14,
        "year": 1990,
    }
    return KeyDate(**{**fields, **overrides})


def stored_person(store: Store, **overrides: Any) -> Person:
    person = a_person(**overrides)
    store.save_person(person)
    return person


def stored_ana_with_a_march_sixth_birthday(store: Store) -> Person:
    ana = stored_person(store, name="Ana", aliases=())
    store.save_key_date(a_key_date(person_id=ana.id, month=3, day=6, year=1993))
    return ana


def stored_gift_idea(store: Store, person: Person, title: str, **overrides: Any) -> None:
    fields: dict[str, Any] = {
        "id": title.replace(" ", "-"),
        "title": title,
        "item_type": ItemType.GIFT,
    }
    item = stored(store, an_item(**{"stage": Stage.WANT_TO, **fields, **overrides}))
    store.link(item.id, person.id)


def a_person_date_reminder(**overrides: Any) -> PersonDateReminder:
    person = overrides.pop("person", None) or a_person(name="Ana", aliases=())
    key_date = overrides.pop("key_date", None) or a_key_date(
        person_id=person.id, month=3, day=6, year=1993
    )
    fields: dict[str, Any] = {
        "person": person,
        "key_date": key_date,
        "on": date(2027, 3, 6),
        "lead": 0,
        "gift_ideas": (),
        "due_at": in_los_angeles(date(2027, 3, 6), 9),
    }
    return PersonDateReminder(**{**fields, **overrides})


def ids_of_people(people: list[Person]) -> list[str]:
    return [person.id for person in people]


def a_directory(store: MemoryStore | None = None) -> PeopleDirectory:
    return PeopleDirectory(
        MemoryStore() if store is None else store, sequential_ids(), lambda: BASE
    )
