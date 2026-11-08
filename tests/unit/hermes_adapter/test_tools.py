import json
from typing import Any

import pytest
from app_builders import stored
from builders import BASE, an_item
from fakes.store_factories import FreshStore

from stash.domain import ItemType, Stage
from stash.hermes_adapter.tool_spec import TOOLSET
from stash.hermes_adapter.tools import LIST_SCHEMA, SEARCH_SCHEMA, StashTools

LOGGER = "stash.hermes_adapter.tools"
NOT_DICTS = [None, "ramen", ["ramen"], 3]


def ramen_and_dune() -> FreshStore:
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


def searched(args: Any, store: FreshStore | None = None) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(StashTools(store or ramen_and_dune()).search(args))
    return answer


def listed(args: Any, store: FreshStore | None = None) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(StashTools(store or ramen_and_dune()).list_items(args))
    return answer


def ids(answer: dict[str, Any]) -> list[str]:
    return [item["id"] for item in answer["items"]]


def test_the_toolset_is_called_stash() -> None:
    # Assert
    assert TOOLSET == "stash"


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


def test_list_leaves_non_ascii_titles_unescaped() -> None:
    # Setup
    store = stored(an_item(title="渋谷のラーメン"))

    # Execute
    raw = StashTools(store).list_items({})

    # Assert
    assert "渋谷のラーメン" in raw


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
