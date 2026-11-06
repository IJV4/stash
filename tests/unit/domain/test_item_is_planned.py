import pytest
from builders import an_item_at

from stash.domain import Stage


@pytest.mark.parametrize("stage", list(Stage))
def test_an_item_is_planned_only_in_the_planned_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    assert item.is_planned is (stage is Stage.PLANNED)
