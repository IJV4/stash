import asyncio
from collections.abc import Mapping
from typing import Any

import pytest
from app_builders import an_app, stored
from builders import an_item, an_outcome
from capture_builders import sequential_ids
from fakes.hermes_ctx import RegisteredTool
from hermes_registration_rig import register_stash
from hermes_rig import called
from people_builders import a_person
from tool_rig import calling

from stash.domain import Person, Stage

ITEM_ID = "i1"
LONG_TEXT = "x" * 2048
_ids = sequential_ids()
FIRST_ID, SECOND_ID = _ids(), _ids()


class PeopleSession:
    def __init__(self) -> None:
        kept_mug = an_item(
            id=ITEM_ID, capture_id="c1", title="Ceramic mug", stage=Stage.DONE, kept=True
        )
        self.store = stored(kept_mug)
        self.store.add_outcome(an_outcome(item_id=ITEM_ID))
        self.plugin = register_stash(an_app(store=self.store))
        self.tools: Mapping[str, RegisteredTool] = self.plugin.ctx.tools

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return calling(self.tools, tool, arguments)

    def people_command(self) -> str:
        return asyncio.run(called(self.plugin.ctx.commands["people"], ""))

    def command(self, name: str) -> str:
        return asyncio.run(called(self.plugin.ctx.commands[name], ""))

    def added(self, name: str, **arguments: Any) -> str:
        return str(self.call("stash_add_person", {"name": name, **arguments})["person"]["id"])

    def snapshot(self) -> tuple[list[Person], list[object], list[object]]:
        people = self.store.list_people()
        dates = [self.store.key_dates_for(person.id) for person in people]
        links = [self.store.items_for(person.id) for person in people]
        return people, dates, links


def test_the_agent_adds_ana_with_her_birthday_and_people_shows_her_next_one() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana", relation="wife")

    # Execute
    session.call("stash_add_key_date", {"person_id": ana, "kind": "birthday", "month": 3, "day": 6})

    # Assert
    assert session.people_command() == "Ana (wife) — birthday Sat Mar 6"


def test_people_with_nobody_saved_says_there_are_no_people_yet() -> None:
    # Setup
    session = PeopleSession()

    # Execute
    text = session.people_command()

    # Assert
    assert text == "No people yet."


def test_the_people_tool_lists_each_person_with_the_id_and_the_next_key_date() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana", relation="wife")
    session.call("stash_add_key_date", {"person_id": ana, "kind": "birthday", "month": 3, "day": 6})

    # Execute
    listed = session.call("stash_people", {})

    # Assert
    assert listed == {
        "people": [
            {
                "id": ana,
                "name": "Ana",
                "relation": "wife",
                "aliases": [],
                "next_key_date": {"kind": "birthday", "label": "", "on": "2027-03-06"},
            }
        ]
    }


def test_linking_an_item_to_a_person_attaches_it_to_her() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")

    # Execute
    session.call("stash_link_person", {"item_id": ITEM_ID, "person_id": ana})

    # Assert
    assert [item.id for item in session.store.items_for(ana)] == [ITEM_ID]


def test_adding_a_person_answers_the_saved_person() -> None:
    # Setup
    session = PeopleSession()

    # Execute
    answer = session.call(
        "stash_add_person", {"name": "Ana", "relation": "wife", "aliases": ["Anita"]}
    )

    # Assert
    assert answer == {
        "person": {"id": FIRST_ID, "name": "Ana", "relation": "wife", "aliases": ["Anita"]}
    }


def test_adding_a_key_date_answers_the_saved_key_date() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")

    # Execute
    answer = session.call(
        "stash_add_key_date",
        {
            "person_id": ana,
            "kind": "other",
            "label": "Moved in",
            "month": 9,
            "day": 1,
            "year": 2020,
        },
    )

    # Assert
    assert answer == {
        "key_date": {
            "id": SECOND_ID,
            "person_id": ana,
            "kind": "other",
            "label": "Moved in",
            "month": 9,
            "day": 1,
            "year": 2020,
        }
    }


def test_linking_answers_the_item_and_person_ids() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")

    # Execute
    answer = session.call("stash_link_person", {"item_id": ITEM_ID, "person_id": ana})

    # Assert
    assert answer == {"linked": {"item_id": ITEM_ID, "person_id": ana}}


def test_removing_a_person_answers_her_id() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")

    # Execute
    answer = session.call("stash_remove_person", {"person_id": ana})

    # Assert
    assert answer == {"removed": ana}


def test_removing_a_person_deletes_her_key_dates_and_keeps_her_linked_items_saved() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")
    session.call("stash_add_key_date", {"person_id": ana, "kind": "birthday", "month": 3, "day": 6})
    session.call("stash_link_person", {"item_id": ITEM_ID, "person_id": ana})

    # Execute
    session.call("stash_remove_person", {"person_id": ana})

    # Assert
    assert (
        session.store.key_dates_for(ana),
        [item.id for item in session.store.list_items(limit=10)],
    ) == ([], [ITEM_ID])


def test_removing_a_person_takes_her_and_her_dates_off_the_list() -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana")
    session.call("stash_add_key_date", {"person_id": ana, "kind": "birthday", "month": 3, "day": 6})

    # Execute
    session.call("stash_remove_person", {"person_id": ana})

    # Assert
    assert session.people_command() == "No people yet."


PRIVATE_PERSON_DETAILS = ("Marguerite", "spouse", "Daisy", "Allergic to nuts")


def test_a_linked_persons_details_never_appear_in_the_item_lists_search_or_library() -> None:
    # Setup
    session = PeopleSession()
    person = a_person(
        id="p9",
        name="Marguerite",
        relation="spouse",
        aliases=("Daisy",),
        notes="Allergic to nuts",
    )
    session.store.save_person(person)
    session.call("stash_link_person", {"item_id": ITEM_ID, "person_id": person.id})

    # Execute
    shown = " ".join(
        [
            session.plugin.ctx.tools["stash_list"].handler({}),
            session.plugin.ctx.tools["stash_search"].handler({"query": "mug"}),
            session.plugin.ctx.tools["stash_library"].handler({}),
            session.command("list"),
            session.command("library"),
        ]
    )

    # Assert
    assert ("Ceramic mug" in shown, [text for text in PRIVATE_PERSON_DETAILS if text in shown]) == (
        True,
        [],
    )


REFUSED_CALLS = [
    ("blank name", "stash_add_person", {"name": "  "}),
    ("a 2 KB name", "stash_add_person", {"name": LONG_TEXT}),
    ("a 2 KB relation", "stash_add_person", {"name": "Bo", "relation": LONG_TEXT}),
    ("six aliases", "stash_add_person", {"name": "Bo", "aliases": list("abcdef")}),
    ("a repeated name", "stash_add_person", {"name": "ana"}),
    ("a name that is an alias", "stash_add_person", {"name": "Anita"}),
    ("an alias that is a name", "stash_add_person", {"name": "Bo", "aliases": ["ANA"]}),
    ("a text alias list", "stash_add_person", {"name": "Bo", "aliases": "Bobby"}),
]


@pytest.mark.parametrize(("_why", "tool", "arguments"), REFUSED_CALLS)
def test_a_refused_add_person_call_answers_an_error_and_stores_nothing(
    _why: str, tool: str, arguments: dict[str, Any]
) -> None:
    # Setup
    session = PeopleSession()
    session.added("Ana", aliases=["Anita"])
    before = session.snapshot()

    # Execute
    answer = session.call(tool, arguments)

    # Assert
    assert (list(answer), session.snapshot()) == (["error"], before)


def key_date_call(**overrides: Any) -> dict[str, Any]:
    return {"kind": "birthday", "month": 3, "day": 6, **overrides}


REFUSED_KEY_DATES = [
    ("April 31st", key_date_call(month=4, day=31)),
    ("Feb 29th of a common year", key_date_call(month=2, day=29, year=2023)),
    ("an unknown kind", key_date_call(kind="holiday")),
    ("a month in words", key_date_call(month="March")),
    ("a 2 KB label", key_date_call(kind="other", label=LONG_TEXT)),
    ("an unknown person", key_date_call(person_id="ghost")),
]


@pytest.mark.parametrize(("_why", "arguments"), REFUSED_KEY_DATES)
def test_a_refused_add_key_date_call_answers_an_error_and_stores_no_date(
    _why: str, arguments: dict[str, Any]
) -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana", aliases=["Anita"])
    before = session.snapshot()

    # Execute
    answer = session.call("stash_add_key_date", {"person_id": ana, **arguments})

    # Assert
    assert (list(answer), session.snapshot()) == (["error"], before)


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("stash_link_person", {"item_id": "ghost", "person_id": "{ana}"}),
        ("stash_link_person", {"item_id": ITEM_ID, "person_id": "ghost"}),
        ("stash_remove_person", {"person_id": "ghost"}),
    ],
)
def test_an_unknown_id_in_a_link_or_remove_call_answers_an_error_and_changes_nothing(
    tool: str, arguments: dict[str, Any]
) -> None:
    # Setup
    session = PeopleSession()
    ana = session.added("Ana", aliases=["Anita"])
    before = session.snapshot()
    resolved = {name: value.format(ana=ana) for name, value in arguments.items()}

    # Execute
    answer = session.call(tool, resolved)

    # Assert
    assert (list(answer), session.snapshot()) == (["error"], before)


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("stash_link_person", {"item_id": "ghost-item", "person_id": "ghost-person"}),
        ("stash_remove_person", {"person_id": "ghost-person"}),
    ],
)
def test_the_error_for_an_unknown_id_names_what_was_not_found(
    tool: str, arguments: dict[str, Any]
) -> None:
    # Setup
    session = PeopleSession()

    # Execute
    answer = session.call(tool, arguments)

    # Assert
    assert answer["error"].startswith("no ")
