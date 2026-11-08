from datetime import timedelta

import pytest
from builders import (
    NAIVE,
    UNSAFE_WIRE_IDS,
)
from step_builders import a_nudge

from stash.domain import NudgeKind
from stash.domain.nudge import MAX_NUDGE_SUBJECT_LENGTH
from stash.domain.wire import MAX_ID_LENGTH

ONE_DAY = timedelta(days=1)
NUDGE_KIND_VALUES = [
    (NudgeKind.STEP, "step"),
    (NudgeKind.ITEM_DATE, "item_date"),
    (NudgeKind.FOLLOWUP, "followup"),
    (NudgeKind.DIGEST, "digest"),
    (NudgeKind.STUCK, "stuck"),
    (NudgeKind.FORGOTTEN, "forgotten"),
    (NudgeKind.PERSON_DATE, "person_date"),
]
UNSAFE_SUBJECT_IDS = (
    *(unsafe for unsafe in UNSAFE_WIRE_IDS if len(unsafe) <= MAX_ID_LENGTH),
    "x" * (MAX_NUDGE_SUBJECT_LENGTH + 1),
)


@pytest.mark.parametrize(("kind", "value"), NUDGE_KIND_VALUES)
def test_each_nudge_kind_is_written_as_its_lowercase_name(kind: NudgeKind, value: str) -> None:
    # Assert
    assert kind.value == value


def test_there_are_exactly_seven_nudge_kinds() -> None:
    # Assert
    assert len(NudgeKind) == len(NUDGE_KIND_VALUES)


def test_a_nudge_refuses_a_naive_due_at() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="due_at must be timezone-aware"):
        a_nudge(due_at=NAIVE)


@pytest.mark.parametrize("subject_id", UNSAFE_SUBJECT_IDS)
def test_a_nudge_refuses_a_subject_id_that_cannot_travel_in_callback_data(
    subject_id: str,
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="nudge subject id"):
        a_nudge(subject_id=subject_id)
