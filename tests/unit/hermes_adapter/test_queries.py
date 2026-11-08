import pytest
from app_builders import stored
from builders import BASE, an_item
from fakes.store_factories import FreshStore

from stash.domain import ItemType, Stage
from stash.hermes_adapter.queries import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ItemQuery,
    checked_limit,
    item_type_from_text,
)
from stash.hermes_adapter.tool_arguments import ToolArguments


def three_items() -> FreshStore:
    return stored(
        an_item(id="a", capture_id="ca", title="Ichiran", stage=Stage.WANT_TO, created_at=BASE),
        an_item(
            id="b",
            capture_id="cb",
            title="Lemon chicken",
            item_type=ItemType.RECIPE,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=1),
        ),
        an_item(
            id="c",
            capture_id="cc",
            title="Tonkatsu",
            stage=Stage.INBOX,
            created_at=BASE.replace(minute=2),
        ),
    )


def fetched_ids(query: ItemQuery) -> list[str]:
    return [item.id for item in query.fetch(three_items())]


def test_the_default_limit_is_20_and_the_maximum_50() -> None:
    # Assert
    assert (DEFAULT_LIMIT, MAX_LIMIT) == (20, 50)


def test_a_query_with_limit_1_and_a_query_with_limit_50_are_accepted() -> None:
    # Execute
    limits = [ItemQuery(None, None, 1).limit, ItemQuery(None, None, 50).limit]

    # Assert
    assert limits == [1, 50]


def test_a_limit_check_returns_a_limit_within_bounds_unchanged() -> None:
    # Execute
    limit = checked_limit(MAX_LIMIT)

    # Assert
    assert limit == MAX_LIMIT


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


def test_fetch_returns_the_newest_items_first() -> None:
    # Execute
    ids = fetched_ids(ItemQuery(None, None, 20))

    # Assert
    assert ids == ["c", "b", "a"]


def test_fetch_narrows_to_a_stage() -> None:
    # Execute
    ids = fetched_ids(ItemQuery(Stage.WANT_TO, None, 20))

    # Assert
    assert ids == ["b", "a"]


def test_fetch_narrows_to_a_type() -> None:
    # Execute
    ids = fetched_ids(ItemQuery(None, ItemType.RECIPE, 20))

    # Assert
    assert ids == ["b"]


def test_fetch_caps_the_number_of_items_at_the_limit() -> None:
    # Execute
    ids = fetched_ids(ItemQuery(None, None, 2))

    # Assert
    assert ids == ["c", "b"]


def test_from_text_of_nothing_is_the_default_query() -> None:
    # Execute
    query = ItemQuery.from_text("")

    # Assert
    assert query == ItemQuery(None, None, DEFAULT_LIMIT)


def test_from_text_of_only_whitespace_is_the_default_query() -> None:
    # Execute
    query = ItemQuery.from_text("   \t ")

    # Assert
    assert query == ItemQuery(None, None, DEFAULT_LIMIT)


@pytest.mark.parametrize("raw", ["want_to", "Want To", "want-to", "WANT_TO", "  want   to "])
def test_from_text_accepts_the_want_to_stage_in_any_spelling(raw: str) -> None:
    # Execute
    query = ItemQuery.from_text(raw)

    # Assert
    assert query.stage is Stage.WANT_TO


def test_from_text_trims_the_stage() -> None:
    # Execute
    query = ItemQuery.from_text("  planned ")

    # Assert
    assert query.stage is Stage.PLANNED


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


def test_from_arguments_of_nothing_is_the_default_query() -> None:
    # Execute
    query = ItemQuery.from_arguments(ToolArguments.of({}))

    # Assert
    assert query == ItemQuery(None, None, DEFAULT_LIMIT)


def test_from_arguments_reads_stage_type_and_limit() -> None:
    # Execute
    query = ItemQuery.from_arguments(
        ToolArguments.of({"stage": "done", "item_type": "recipe", "limit": 7})
    )

    # Assert
    assert query == ItemQuery(Stage.DONE, ItemType.RECIPE, 7)


def test_from_arguments_accepts_a_stage_in_any_case() -> None:
    # Execute
    query = ItemQuery.from_arguments(ToolArguments.of({"stage": " Want-To "}))

    # Assert
    assert query.stage is Stage.WANT_TO


def test_from_arguments_ignores_arguments_it_does_not_know() -> None:
    # Execute
    query = ItemQuery.from_arguments(ToolArguments.of({"limit": 3, "colour": "red"}))

    # Assert
    assert query == ItemQuery(None, None, 3)


@pytest.mark.parametrize("key", ["stage", "item_type", "limit"])
def test_from_arguments_treats_an_explicit_null_as_absent(key: str) -> None:
    # Execute
    query = ItemQuery.from_arguments(ToolArguments.of({key: None}))

    # Assert
    assert query == ItemQuery(None, None, DEFAULT_LIMIT)


def test_from_arguments_refuses_an_unknown_stage_naming_it() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="unknown stage 'soonish'"):
        ItemQuery.from_arguments(ToolArguments.of({"stage": "soonish"}))


def test_from_arguments_refuses_an_unknown_stage_listing_the_valid_ones() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_arguments(ToolArguments.of({"stage": "soonish"}))

    # Assert
    assert all(stage.value in str(refusal.value) for stage in Stage)


def test_from_arguments_refuses_an_unknown_type_naming_it() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="unknown item_type 'spaceship'"):
        ItemQuery.from_arguments(ToolArguments.of({"item_type": "spaceship"}))


def test_from_arguments_refuses_an_unknown_type_listing_the_valid_ones() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_arguments(ToolArguments.of({"item_type": "spaceship"}))

    # Assert
    assert all(item_type.value in str(refusal.value) for item_type in ItemType)


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


def test_an_unknown_item_type_of_5000_characters_is_echoed_cut_to_40_and_an_ellipsis() -> None:
    # Execute
    with pytest.raises(ValueError) as refusal:
        ItemQuery.from_arguments(ToolArguments.of({"item_type": "y" * 5000}))

    # Assert
    assert str(refusal.value).startswith(f"unknown item_type '{'y' * 40}…' (valid:")


@pytest.mark.parametrize("raw", ["", "   \t "])
def test_item_type_from_nothing_is_no_type(raw: str) -> None:
    # Execute
    item_type = item_type_from_text(raw)

    # Assert
    assert item_type is None


@pytest.mark.parametrize("raw", ["recipe", " Recipe ", "RECIPE"])
def test_item_type_from_text_ignores_case_and_surrounding_space(raw: str) -> None:
    # Execute
    item_type = item_type_from_text(raw)

    # Assert
    assert item_type is ItemType.RECIPE


LABEL_SPELLINGS = [
    ("recipes", ItemType.RECIPE),
    (" RECIPES ", ItemType.RECIPE),
    ("Learning", ItemType.LEARN),
    ("learning", ItemType.LEARN),
    ("learn", ItemType.LEARN),
    ("Activities", ItemType.ACTIVITY),
    ("activity", ItemType.ACTIVITY),
    ("Other", ItemType.OTHER),
]


@pytest.mark.parametrize(("raw", "expected"), LABEL_SPELLINGS)
def test_item_type_from_text_accepts_the_value_or_the_label_the_library_prints(
    raw: str, expected: ItemType
) -> None:
    # Execute
    item_type = item_type_from_text(raw)

    # Assert
    assert item_type is expected


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
