import pytest

from stash.domain import Stage
from stash.hermes_adapter.queries import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ItemQuery,
    checked_limit,
    item_type_from_text,
)
from stash.hermes_adapter.tool_arguments import ToolArguments


def test_the_default_limit_is_20_and_the_maximum_50() -> None:
    # Assert
    assert (DEFAULT_LIMIT, MAX_LIMIT) == (20, 50)


@pytest.mark.parametrize("limit", [0, MAX_LIMIT + 1])
def test_a_limit_check_refuses_a_limit_out_of_bounds(limit: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="between 1 and 50"):
        checked_limit(limit)


def test_a_limit_of_0_is_refused() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery(None, None, 0)

    # Assert
    assert "between 1 and 50" in str(refusal.value)


def test_a_limit_of_51_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="between 1 and 50"):
        ItemQuery(None, None, 51)


def test_from_text_with_an_unknown_stage_names_the_problem() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="unknown stage 'soonish'"):
        ItemQuery.from_text("soonish")


def test_from_text_with_an_unknown_stage_lists_the_valid_stages() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_text("soonish")

    # Assert
    assert all(stage.value in str(refusal.value) for stage in Stage)


def test_from_arguments_refuses_a_stage_that_is_not_text() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="stage must be text"):
        ItemQuery.from_arguments(ToolArguments.of({"stage": 3}))


def test_from_arguments_refuses_a_type_that_is_not_text() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item_type must be text"):
        ItemQuery.from_arguments(ToolArguments.of({"item_type": ["place"]}))


@pytest.mark.parametrize("limit", [True, False, "5", 2.5])
def test_from_arguments_refuses_a_limit_that_is_not_an_integer(limit: object) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be an integer"):
        ItemQuery.from_arguments(ToolArguments.of({"limit": limit}))


@pytest.mark.parametrize("limit", [0, 51, -3])
def test_from_arguments_refuses_a_limit_out_of_range(limit: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="between 1 and 50"):
        ItemQuery.from_arguments(ToolArguments.of({"limit": limit}))


def test_an_unknown_stage_of_5000_characters_is_echoed_cut_to_40_and_an_ellipsis() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_text("x" * 5000)

    # Assert
    assert str(refusal.value).startswith(f"unknown stage '{'x' * 40}…' (valid:")


def test_an_unknown_stage_of_exactly_40_characters_is_echoed_whole() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_text("x" * 40)

    # Assert
    assert str(refusal.value).startswith(f"unknown stage '{'x' * 40}' (valid:")


def test_item_type_from_text_with_an_unknown_type_lists_the_labels_in_plain_words() -> None:
    # Execute / Assert
    with pytest.raises(ValueError) as refusal:
        item_type_from_text("spaceship")

    # Assert
    assert str(refusal.value) == (
        "unknown type 'spaceship' (try: places, recipes, purchases, learning, books, media, "
        "ideas, plans, activities, gifts, other)"
    )


def test_item_type_from_text_echoes_an_overlong_unknown_type_cut_to_40_and_an_ellipsis() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        item_type_from_text("y" * 5000)

    # Assert
    assert str(refusal.value).startswith(f"unknown type '{'y' * 40}…' (try:")
