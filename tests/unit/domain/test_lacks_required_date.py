from datetime import date

import pytest

from stash.domain import Stage, lacks_required_date

A_DATE = date(2026, 11, 14)


def test_a_planned_stage_without_a_date_lacks_its_required_date() -> None:
    # Execute / Assert
    assert lacks_required_date(Stage.PLANNED, None) is True


def test_a_planned_stage_with_a_date_does_not_lack_its_required_date() -> None:
    # Execute / Assert
    assert lacks_required_date(Stage.PLANNED, A_DATE) is False


@pytest.mark.parametrize("stage", [stage for stage in Stage if stage is not Stage.PLANNED])
def test_a_stage_other_than_planned_never_needs_a_date(stage: Stage) -> None:
    # Execute / Assert
    assert lacks_required_date(stage, None) is False
