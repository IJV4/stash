from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

import pytest
from builders import (
    BASE,
    LATER,
    NAIVE,
    UNSAFE_WIRE_IDS,
    a_parent_item,
    an_item,
    an_item_at,
)

from stash.domain.item import DROP_REASON_LIMIT, Item, Stage

NON_DROPPED_STAGES = tuple(stage for stage in Stage if stage is not Stage.DROPPED)

Transition = Callable[[Item, datetime], Item]


TRANSITIONS = [
    pytest.param(lambda item, now: item.completed(now), an_item(), id="completed"),
    pytest.param(lambda item, now: item.dropped("Not for me", now), an_item(), id="dropped"),
    pytest.param(
        lambda item, now: item.kept_as(True, now), an_item(stage=Stage.DONE), id="kept_as"
    ),
    pytest.param(
        lambda item, now: item.grouped_under(a_parent_item(), now), an_item(), id="grouped_under"
    ),
    pytest.param(lambda item, now: item.ungrouped(now), an_item(parent_id="p1"), id="ungrouped"),
]


def test_item_with_a_parent_id_equal_to_its_own_id_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="groups are one level deep"):
        an_item(id="i1", parent_id="i1")


@pytest.mark.parametrize("parent_id", UNSAFE_WIRE_IDS)
def test_item_refuses_a_parent_id_that_cannot_travel_in_callback_data(parent_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item parent id"):
        an_item(parent_id=parent_id)


@pytest.mark.parametrize("stage", NON_DROPPED_STAGES)
def test_item_with_a_drop_reason_outside_the_dropped_stage_raises_value_error(
    stage: Stage,
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="drop_reason is only for dropped items"):
        an_item_at(stage, drop_reason="Not for me")


def test_a_dropped_item_refuses_a_drop_reason_over_the_maximum_length() -> None:
    # Execute / Assert
    with pytest.raises(
        ValueError, match=f"drop_reason must be at most {DROP_REASON_LIMIT} characters"
    ):
        an_item(stage=Stage.DROPPED, drop_reason="r" * (DROP_REASON_LIMIT + 1))


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_a_dropped_item_refuses_a_blank_drop_reason(blank: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="drop_reason must not be blank"):
        an_item(stage=Stage.DROPPED, drop_reason=blank)


@pytest.mark.parametrize("transition, item", TRANSITIONS)
def test_every_lifecycle_transition_stamps_updated_at_with_now(
    transition: Transition, item: Item
) -> None:
    # Execute
    result = transition(item, LATER)

    # Assert
    assert result.updated_at == LATER


@pytest.mark.parametrize("transition, item", TRANSITIONS)
def test_every_lifecycle_transition_keeps_created_at(transition: Transition, item: Item) -> None:
    # Execute
    result = transition(item, LATER)

    # Assert
    assert result.created_at == BASE


@pytest.mark.parametrize("transition, item", TRANSITIONS)
def test_every_lifecycle_transition_leaves_the_original_item_unchanged(
    transition: Transition, item: Item
) -> None:
    # Setup
    snapshot = replace(item)

    # Execute
    transition(item, LATER)

    # Assert
    assert item == snapshot


@pytest.mark.parametrize("transition, item", TRANSITIONS)
def test_every_lifecycle_transition_with_naive_now_raises_value_error(
    transition: Transition, item: Item
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at"):
        transition(item, NAIVE)
