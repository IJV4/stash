from datetime import date, datetime, timedelta

import pytest
from builders import (
    FALL_BACK_DAY,
    NAIVE,
    PLUS_FIVE,
    SPRING_FORWARD_DAY,
    UNSAFE_WIRE_IDS,
    in_los_angeles,
)
from step_builders import DUE_AT, a_nudge

from stash.domain import NudgeKey, NudgeKind
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
LONGEST_PERSON_DATE_SUBJECT = f"{'k' * MAX_ID_LENGTH}@2027-03-06#365"


def nine_in_los_angeles(day: date) -> datetime:
    return in_los_angeles(day, 9)


@pytest.mark.parametrize(("kind", "value"), NUDGE_KIND_VALUES)
def test_each_nudge_kind_is_written_as_its_lowercase_name(kind: NudgeKind, value: str) -> None:
    # Assert
    assert kind.value == value


def test_there_are_exactly_seven_nudge_kinds() -> None:
    # Assert
    assert len(NudgeKind) == len(NUDGE_KIND_VALUES)


def test_a_nudge_key_is_the_kind_the_subject_and_the_utc_instant() -> None:
    # Setup
    nudge = a_nudge(kind=NudgeKind.ITEM_DATE, subject_id="i7")

    # Execute
    key: NudgeKey = nudge.key

    # Assert
    assert key == ("item_date", "i7", "2026-11-02T09:00:00.000000+00:00")


def test_a_nudge_key_names_its_kind_subject_and_due_instant() -> None:
    # Setup
    key = a_nudge(kind=NudgeKind.ITEM_DATE, subject_id="i7").key

    # Execute / Assert
    assert (key.kind, key.subject_id, key.due_at) == (
        "item_date",
        "i7",
        "2026-11-02T09:00:00.000000+00:00",
    )


def test_the_same_instant_written_in_another_offset_gives_the_same_key() -> None:
    # Setup
    in_plus_five = DUE_AT.astimezone(PLUS_FIVE)

    # Execute
    key = a_nudge(due_at=in_plus_five).key

    # Assert
    assert key == a_nudge(due_at=DUE_AT).key


def test_nudges_for_different_subjects_have_different_keys() -> None:
    # Execute / Assert
    assert a_nudge(subject_id="s1").key != a_nudge(subject_id="s2").key


def test_nudges_of_different_kinds_have_different_keys() -> None:
    # Execute / Assert
    assert a_nudge(kind=NudgeKind.STEP).key != a_nudge(kind=NudgeKind.STUCK).key


def test_nudges_due_a_microsecond_apart_have_different_keys() -> None:
    # Execute / Assert
    assert a_nudge(due_at=DUE_AT).key != a_nudge(due_at=DUE_AT + timedelta(microseconds=1)).key


def test_nine_local_on_the_spring_forward_day_has_its_own_utc_key() -> None:
    # Execute
    key = a_nudge(due_at=nine_in_los_angeles(SPRING_FORWARD_DAY)).key

    # Assert
    assert key == ("step", "s1", "2027-03-14T16:00:00.000000+00:00")


def test_nine_local_the_day_before_spring_forward_has_its_own_utc_key() -> None:
    # Execute
    key = a_nudge(due_at=nine_in_los_angeles(SPRING_FORWARD_DAY - ONE_DAY)).key

    # Assert
    assert key == ("step", "s1", "2027-03-13T17:00:00.000000+00:00")


def test_nine_local_on_the_fall_back_day_has_its_own_utc_key() -> None:
    # Execute
    key = a_nudge(due_at=nine_in_los_angeles(FALL_BACK_DAY)).key

    # Assert
    assert key == ("step", "s1", "2027-11-07T17:00:00.000000+00:00")


def test_nine_local_the_day_before_fall_back_has_its_own_utc_key() -> None:
    # Execute
    key = a_nudge(due_at=nine_in_los_angeles(FALL_BACK_DAY - ONE_DAY)).key

    # Assert
    assert key == ("step", "s1", "2027-11-06T16:00:00.000000+00:00")


def test_consecutive_local_days_across_a_dst_change_have_distinct_keys() -> None:
    # Setup
    days = (SPRING_FORWARD_DAY + timedelta(days=offset) for offset in (-2, -1, 0, 1))
    keys = {a_nudge(due_at=nine_in_los_angeles(day)).key for day in days}

    # Execute / Assert
    assert len(keys) == 4


def test_a_nudge_key_is_stable_across_rebuilding_the_nudge() -> None:
    # Execute / Assert
    assert (
        a_nudge(due_at=nine_in_los_angeles(FALL_BACK_DAY)).key
        == a_nudge(due_at=nine_in_los_angeles(FALL_BACK_DAY)).key
    )


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


def test_a_nudge_accepts_a_longest_key_date_id_with_its_occurrence_and_lead() -> None:
    # Execute
    nudge = a_nudge(kind=NudgeKind.PERSON_DATE, subject_id=LONGEST_PERSON_DATE_SUBJECT)

    # Assert
    assert nudge.subject_id == LONGEST_PERSON_DATE_SUBJECT


@pytest.mark.parametrize("title", ["", "   ", "\n"])
def test_a_nudge_refuses_a_blank_title(title: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="title must not be blank"):
        a_nudge(title=title)


def test_a_key_built_from_its_parts_is_the_key_of_the_matching_nudge() -> None:
    # Setup
    nudge = a_nudge(kind=NudgeKind.FORGOTTEN, subject_id="i7")

    # Execute
    key = NudgeKey.of(NudgeKind.FORGOTTEN, "i7", DUE_AT)

    # Assert
    assert key == nudge.key


def test_a_key_carries_the_name_of_its_kind() -> None:
    # Execute
    key = NudgeKey.of(NudgeKind.FORGOTTEN, "i7", DUE_AT)

    # Assert
    assert key.kind == "forgotten"


def test_a_key_writes_the_instant_in_utc() -> None:
    # Execute
    key = NudgeKey.of(NudgeKind.STEP, "s1", in_los_angeles(date(2026, 11, 2), 9))

    # Assert
    assert key.due_at == "2026-11-02T17:00:00.000000+00:00"
