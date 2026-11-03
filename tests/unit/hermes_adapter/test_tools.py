import json
import logging
from datetime import date
from typing import Any

import pytest
from app_builders import stored
from builders import BASE, an_item
from fakes.failing_list_store import FailingListStore
from fakes.failing_search_store import FailingSearchStore
from fakes.memory_store import MemoryStore
from log_records import recording_logs

from stash.domain import ItemType, Stage
from stash.hermes_adapter.tools import LIST_SCHEMA, SEARCH_SCHEMA, TOOLSET, StashTools

LOGGER = "stash.hermes_adapter.tools"
NOT_DICTS = [None, "ramen", ["ramen"], 3]


def ramen_and_dune() -> MemoryStore:
    return stored(
        an_item(id="a", capture_id="ca", title="Ramen in Shibuya", created_at=BASE),
        an_item(
            id="b",
            capture_id="cb",
            title="Dune",
            item_type=ItemType.BOOK,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=1),
        ),
        an_item(
            id="c",
            capture_id="cc",
            title="Tonkotsu ramen at home",
            item_type=ItemType.RECIPE,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=2),
        ),
    )


def searched(args: Any, store: MemoryStore | None = None) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(StashTools(store or ramen_and_dune()).search(args))
    return answer


def listed(args: Any, store: MemoryStore | None = None) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(StashTools(store or ramen_and_dune()).list_items(args))
    return answer


def ids(answer: dict[str, Any]) -> list[str]:
    return [item["id"] for item in answer["items"]]


def test_the_toolset_is_called_stash() -> None:
    # Assert
    assert TOOLSET == "stash"


def test_search_answers_the_items_in_the_documented_shape() -> None:
    # Setup
    store = stored(
        an_item(id="a", capture_id="ca", title="Dune", item_type=ItemType.BOOK, date=None)
    )

    # Execute
    answer = searched({"query": "dune"}, store)

    # Assert
    assert answer == {
        "items": [{"id": "a", "type": "book", "title": "Dune", "stage": "inbox", "date": None}]
    }


def test_search_answers_the_date_of_a_planned_item_as_iso_text() -> None:
    # Setup
    store = stored(an_item(title="Dune", stage=Stage.PLANNED, date=date(2026, 11, 5)))

    # Execute
    answer = searched({"query": "dune"}, store)

    # Assert
    assert answer["items"][0]["date"] == "2026-11-05"


def test_search_finds_matches_newest_first() -> None:
    # Execute
    answer = searched({"query": "ramen"})

    # Assert
    assert ids(answer) == ["c", "a"]


def test_search_without_a_match_answers_no_items() -> None:
    # Execute
    answer = searched({"query": "sushi"})

    # Assert
    assert answer == {"items": []}


def test_search_ignores_the_case_of_the_query() -> None:
    # Execute
    answer = searched({"query": "RAMEN"})

    # Assert
    assert ids(answer) == ["c", "a"]


def test_search_trims_the_query() -> None:
    # Execute
    answer = searched({"query": "  dune \n"})

    # Assert
    assert ids(answer) == ["b"]


def test_search_honours_the_limit() -> None:
    # Execute
    answer = searched({"query": "ramen", "limit": 1})

    # Assert
    assert ids(answer) == ["c"]


def test_search_leaves_non_ascii_titles_unescaped() -> None:
    # Setup
    store = stored(an_item(title="渋谷のラーメン"))

    # Execute
    raw = StashTools(store).search({"query": "渋谷"})

    # Assert
    assert "渋谷のラーメン" in raw


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_search_with_a_blank_query_answers_an_error(query: str) -> None:
    # Execute
    answer = searched({"query": query})

    # Assert
    assert answer == {"error": "query must not be blank"}


@pytest.mark.parametrize("args", [{}, {"query": None}, {"query": 5}, {"query": ["a"]}])
def test_search_with_a_query_that_is_not_text_answers_an_error(args: dict[str, Any]) -> None:
    # Execute
    answer = searched(args)

    # Assert
    assert answer == {"error": "query must be text"}


def test_search_accepts_a_query_of_200_characters() -> None:
    # Execute
    answer = searched({"query": "x" * 200})

    # Assert
    assert answer == {"items": []}


def test_search_with_a_query_over_200_characters_answers_an_error() -> None:
    # Execute
    answer = searched({"query": "x" * 201})

    # Assert
    assert answer == {"error": "query must be at most 200 characters"}


def test_search_with_a_limit_out_of_range_answers_an_error() -> None:
    # Execute
    answer = searched({"query": "ramen", "limit": 51})

    # Assert
    assert answer == {"error": "limit must be between 1 and 50"}


@pytest.mark.parametrize("args", NOT_DICTS)
def test_search_with_arguments_that_are_not_a_dict_answers_an_error(args: Any) -> None:
    # Execute
    answer = searched(args)

    # Assert
    assert answer == {"error": "arguments must be an object"}


def test_search_tolerates_extra_keyword_arguments_from_hermes() -> None:
    # Execute
    raw = StashTools(ramen_and_dune()).search({"query": "dune"}, task_id="t1", session="s")

    # Assert
    assert json.loads(raw)["items"][0]["id"] == "b"


def test_search_answers_an_error_when_the_store_fails() -> None:
    # Execute
    answer = searched({"query": "dune"}, FailingSearchStore())

    # Assert
    assert answer == {"error": "the stash could not be read"}


def test_search_logs_the_exception_when_the_store_fails() -> None:
    # Setup
    with recording_logs(LOGGER) as logs:
        # Execute
        searched({"query": "dune"}, FailingSearchStore())

    # Assert
    assert [level for level, _ in logs.entries()] == [logging.ERROR]


def test_list_answers_everything_newest_first() -> None:
    # Execute
    answer = listed({})

    # Assert
    assert ids(answer) == ["c", "b", "a"]


def test_list_answers_the_items_in_the_documented_shape() -> None:
    # Execute
    answer = listed({"item_type": "book"})

    # Assert
    assert answer == {
        "items": [{"id": "b", "type": "book", "title": "Dune", "stage": "want_to", "date": None}]
    }


def test_list_narrows_to_a_stage() -> None:
    # Execute
    answer = listed({"stage": "want_to"})

    # Assert
    assert ids(answer) == ["c", "b"]


def test_list_narrows_to_a_type() -> None:
    # Execute
    answer = listed({"item_type": "recipe"})

    # Assert
    assert ids(answer) == ["c"]


def test_list_honours_the_limit() -> None:
    # Execute
    answer = listed({"limit": 2})

    # Assert
    assert ids(answer) == ["c", "b"]


def test_list_leaves_non_ascii_titles_unescaped() -> None:
    # Setup
    store = stored(an_item(title="渋谷のラーメン"))

    # Execute
    raw = StashTools(store).list_items({})

    # Assert
    assert "渋谷のラーメン" in raw


def test_list_with_an_unknown_stage_answers_an_error_naming_it() -> None:
    # Execute
    answer = listed({"stage": "soonish"})

    # Assert
    assert answer["error"].startswith("unknown stage 'soonish'")


def test_list_with_an_unknown_type_answers_an_error_naming_it() -> None:
    # Execute
    answer = listed({"item_type": "spaceship"})

    # Assert
    assert answer["error"].startswith("unknown item_type 'spaceship'")


def test_list_with_a_5000_character_stage_answers_an_error_that_does_not_echo_it_whole() -> None:
    # Execute
    answer = listed({"stage": "z" * 5000})

    # Assert
    assert len(answer["error"]) < 200


def test_list_with_a_limit_that_is_not_an_integer_answers_an_error() -> None:
    # Execute
    answer = listed({"limit": "5"})

    # Assert
    assert answer == {"error": "limit must be an integer"}


@pytest.mark.parametrize("args", NOT_DICTS)
def test_list_with_arguments_that_are_not_a_dict_answers_an_error(args: Any) -> None:
    # Execute
    answer = listed(args)

    # Assert
    assert answer == {"error": "arguments must be an object"}


def test_list_tolerates_extra_keyword_arguments_from_hermes() -> None:
    # Execute
    raw = StashTools(ramen_and_dune()).list_items({"limit": 1}, task_id="t1")

    # Assert
    assert json.loads(raw)["items"][0]["id"] == "c"


def test_list_answers_an_error_when_the_store_fails() -> None:
    # Execute
    answer = listed({}, FailingListStore())

    # Assert
    assert answer == {"error": "the stash could not be read"}


def test_list_logs_the_exception_when_the_store_fails() -> None:
    # Setup
    with recording_logs(LOGGER) as logs:
        # Execute
        listed({}, FailingListStore())

    # Assert
    assert [level for level, _ in logs.entries()] == [logging.ERROR]


def test_the_search_schema_names_the_tool_stash_search() -> None:
    # Assert
    assert SEARCH_SCHEMA["name"] == "stash_search"


def test_the_list_schema_names_the_tool_stash_list() -> None:
    # Assert
    assert LIST_SCHEMA["name"] == "stash_list"


@pytest.mark.parametrize("schema", [SEARCH_SCHEMA, LIST_SCHEMA])
def test_every_schema_has_a_description(schema: dict[str, Any]) -> None:
    # Assert
    assert schema["description"].strip()


@pytest.mark.parametrize("schema", [SEARCH_SCHEMA, LIST_SCHEMA])
def test_every_schema_describes_an_object_of_parameters(schema: dict[str, Any]) -> None:
    # Assert
    assert schema["parameters"]["type"] == "object"


def test_the_search_schema_requires_the_query() -> None:
    # Assert
    assert SEARCH_SCHEMA["parameters"]["required"] == ["query"]


def test_the_search_schema_describes_the_query_as_text_and_the_limit_as_a_bounded_integer() -> None:
    # Execute
    properties = SEARCH_SCHEMA["parameters"]["properties"]

    # Assert
    assert (properties["query"]["type"], properties["limit"]["maximum"]) == ("string", 50)


def test_the_list_schema_requires_nothing() -> None:
    # Assert
    assert "required" not in LIST_SCHEMA["parameters"]


def test_the_list_schema_offers_exactly_the_stages_of_the_domain() -> None:
    # Assert
    assert LIST_SCHEMA["parameters"]["properties"]["stage"]["enum"] == [s.value for s in Stage]


def test_the_list_schema_offers_exactly_the_types_of_the_domain() -> None:
    # Assert
    assert LIST_SCHEMA["parameters"]["properties"]["item_type"]["enum"] == [
        t.value for t in ItemType
    ]


def test_the_list_schema_bounds_the_limit_from_1_to_50() -> None:
    # Execute
    limit = LIST_SCHEMA["parameters"]["properties"]["limit"]

    # Assert
    assert (limit["type"], limit["minimum"], limit["maximum"]) == ("integer", 1, 50)
