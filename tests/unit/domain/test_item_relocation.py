import pytest
from builders import LATER, PLANNED_FOR, an_item, an_item_at

from stash.domain import (
    DROP_REASON_LIMIT,
    MAX_TAKEAWAYS,
    OUTCOME_NOTES_LIMIT,
    PLANNED_NEEDS_DATE,
    TAKEAWAY_LIMIT,
    Stage,
)

DONE_REFUSAL = "done is reached by completing an item"
RELOCATABLE_STAGES = (Stage.INBOX, Stage.WANT_TO, Stage.DOING, Stage.DROPPED)


@pytest.mark.parametrize("stage", RELOCATABLE_STAGES)
def test_relocating_an_item_puts_it_in_the_requested_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    relocated = item.relocated_to(stage, LATER)

    # Assert
    assert relocated.stage is stage


def test_relocating_an_item_stamps_updated_at_with_now() -> None:
    # Execute
    relocated = an_item().relocated_to(Stage.WANT_TO, LATER)

    # Assert
    assert relocated.updated_at == LATER


def test_relocating_an_item_to_planned_keeps_its_date() -> None:
    # Setup
    item = an_item(date=PLANNED_FOR)

    # Execute
    relocated = item.relocated_to(Stage.PLANNED, LATER)

    # Assert
    assert (relocated.stage, relocated.date) == (Stage.PLANNED, PLANNED_FOR)


def test_relocating_an_item_to_done_is_refused_with_the_complete_hint() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=DONE_REFUSAL):
        an_item().relocated_to(Stage.DONE, LATER)


def test_relocating_an_item_to_planned_without_a_date_is_refused_with_the_date_hint() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=PLANNED_NEEDS_DATE):
        an_item().relocated_to(Stage.PLANNED, LATER)


def test_the_limits_the_tool_schemas_advertise_are_exported_from_the_domain() -> None:
    # Execute
    limits = (OUTCOME_NOTES_LIMIT, MAX_TAKEAWAYS, TAKEAWAY_LIMIT, DROP_REASON_LIMIT)

    # Assert
    assert limits == (4000, 20, 500, 300)
