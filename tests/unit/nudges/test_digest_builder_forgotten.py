from datetime import UTC, datetime, timedelta

import pytest
from builders import FALL_BACK_DAY, MICROSECOND, in_los_angeles, stored
from digest_builders import (
    DIGEST_AT,
    ONE_DAY,
    ONE_WEEK,
    a_digest_builder,
    a_due_digest,
    a_forgotten_want_to,
    building,
)
from fakes.store_factories import FreshStore

from stash.domain import Nudge, NudgeKind, Stage
from stash.nudges.digest_builder import PREVIOUS_DIGESTS

CUTOFF = DIGEST_AT - timedelta(days=30)
ALREADY_SHOWN_OLDEST_FIRST = 12


def forgotten_ids(store: FreshStore, at: datetime = DIGEST_AT) -> list[str]:
    return [item.id for item in building(store, at).forgotten]


def shown_in_the_digest_at(store: FreshStore, item_id: str, instant: datetime) -> None:
    store.record_all_sent([Nudge(NudgeKind.FORGOTTEN, item_id, instant, item_id)], instant)


def test_forgotten_items_are_the_want_to_items_untouched_for_the_configured_days_oldest_first() -> (
    None
):
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("newer", updated_at=CUTOFF - timedelta(days=1)))
    stored(store, a_forgotten_want_to("oldest", updated_at=CUTOFF - timedelta(days=9)))
    stored(store, a_forgotten_want_to("recent", updated_at=CUTOFF + timedelta(days=1)))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["oldest", "newer"]


def test_an_item_untouched_for_exactly_the_configured_days_is_not_yet_forgotten() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("on-the-edge", updated_at=CUTOFF))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == []


def test_an_item_untouched_for_a_microsecond_longer_than_the_configured_days_is_forgotten() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("just-forgotten", updated_at=CUTOFF - MICROSECOND))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["just-forgotten"]


def test_an_item_that_is_not_in_want_to_is_never_forgotten() -> None:
    # Setup
    store = FreshStore()
    for stage in (Stage.INBOX, Stage.DOING, Stage.DONE, Stage.DROPPED):
        stored(store, a_forgotten_want_to(f"in-{stage.value}", stage=stage))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == []


def test_the_forgotten_days_come_from_the_nudge_configuration() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("five-days", updated_at=DIGEST_AT - timedelta(days=5)))

    # Execute
    ids = [item.id for item in building(store, forgotten_after_days=3).forgotten]

    # Assert
    assert ids == ["five-days"]


def test_the_forgotten_section_keeps_the_three_oldest_items() -> None:
    # Setup
    store = FreshStore()
    for age in range(4):
        updated = CUTOFF - timedelta(days=10 - age)
        stored(store, a_forgotten_want_to(f"age-{age}", updated_at=updated))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["age-0", "age-1", "age-2"]


@pytest.mark.parametrize("weeks_back", range(1, PREVIOUS_DIGESTS + 1))
def test_an_item_shown_in_one_of_the_previous_four_digests_is_left_out(weeks_back: int) -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("seen"))
    shown_in_the_digest_at(store, "seen", DIGEST_AT - ONE_WEEK * weeks_back)

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == []


def test_an_item_last_shown_five_digests_ago_may_return() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("seen-long-ago"))
    shown_in_the_digest_at(store, "seen-long-ago", DIGEST_AT - ONE_WEEK * (PREVIOUS_DIGESTS + 1))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["seen-long-ago"]


def test_an_item_already_recorded_for_this_very_digest_is_still_in_it_when_it_is_rebuilt() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("sail"))
    shown_in_the_digest_at(store, "sail", DIGEST_AT)

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["sail"]


def test_an_item_recorded_under_another_nudge_kind_is_still_forgotten() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("sail"))
    previous = DIGEST_AT - ONE_WEEK
    store.record_all_sent([Nudge(NudgeKind.STUCK, "sail", previous, "sail")], previous)

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["sail"]


def test_an_item_shown_to_another_digest_instant_than_the_previous_four_may_return() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("sail"))
    shown_in_the_digest_at(store, "sail", DIGEST_AT - ONE_WEEK + timedelta(hours=1))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["sail"]


def test_the_fourth_previous_digest_is_found_across_a_change_of_clocks() -> None:
    # Setup
    store = FreshStore()
    digest_on_the_day_the_clocks_go_back = in_los_angeles(FALL_BACK_DAY, 10).astimezone(UTC)
    fourth_previous_day = FALL_BACK_DAY - timedelta(weeks=PREVIOUS_DIGESTS)
    stored(store, a_forgotten_want_to("sail"))
    shown_in_the_digest_at(store, "sail", in_los_angeles(fourth_previous_day, 10))

    # Execute
    ids = forgotten_ids(store, digest_on_the_day_the_clocks_go_back)

    # Assert
    assert ids == []


def test_enough_items_are_read_to_fill_the_section_when_the_oldest_were_all_shown_before() -> None:
    # Setup
    store = FreshStore()
    for age in range(ALREADY_SHOWN_OLDEST_FIRST + 3):
        updated = CUTOFF - timedelta(days=100 - age)
        stored(store, a_forgotten_want_to(f"age-{age:02d}", updated_at=updated))
    for age in range(ALREADY_SHOWN_OLDEST_FIRST):
        shown_in_the_digest_at(store, f"age-{age:02d}", DIGEST_AT - ONE_WEEK * (age % 4 + 1))

    # Execute
    ids = forgotten_ids(store)

    # Assert
    assert ids == ["age-12", "age-13", "age-14"]


def test_the_forgotten_days_are_counted_back_from_the_digest_instant_not_from_building() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_want_to("not-yet", updated_at=CUTOFF + timedelta(days=1)))
    building_three_days_late = DIGEST_AT + 3 * ONE_DAY

    # Execute
    built = a_digest_builder(store).build(a_due_digest(), building_three_days_late)

    # Assert
    assert built.sections.forgotten == ()
