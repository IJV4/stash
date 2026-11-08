from builders import BASE
from fakes.store_factories import FreshStore
from planning_builders import DATE_NIGHT_ON, RESCHEDULED_ON, a_date_night

from stash.domain import Stage
from stash.planning.declines import Declines

UNDATED = {"stage": Stage.WANT_TO, "date": None}


def test_a_recorded_decline_matches_the_date_it_was_recorded_for() -> None:
    # Setup
    declines = Declines(FreshStore())
    item = a_date_night()
    declines.record(item)

    # Execute
    declined = declines.is_declined(item)

    # Assert
    assert declined is True


def test_a_recorded_decline_does_not_match_a_different_date() -> None:
    # Setup
    declines = Declines(FreshStore())
    item = a_date_night()
    declines.record(item)

    # Execute
    declined = declines.is_declined(item.rescheduled(RESCHEDULED_ON, BASE))

    # Assert
    assert declined is False


def test_an_item_nobody_declined_is_not_declined() -> None:
    # Setup
    declines = Declines(FreshStore())

    # Execute
    declined = declines.is_declined(a_date_night())

    # Assert
    assert declined is False


def test_a_decline_recorded_for_one_item_does_not_match_another_item_on_the_same_date() -> None:
    # Setup
    declines = Declines(FreshStore())
    declines.record(a_date_night(id="date-night"))

    # Execute
    declined = declines.is_declined(a_date_night(id="museum"))

    # Assert
    assert declined is False


def test_an_item_without_a_date_is_never_declined() -> None:
    # Setup
    declines = Declines(FreshStore())
    declines.record(a_date_night())

    # Execute
    declined = declines.is_declined(a_date_night(**UNDATED))

    # Assert
    assert declined is False


def test_recording_a_decline_for_an_item_without_a_date_writes_nothing() -> None:
    # Setup
    store = FreshStore()

    # Execute
    Declines(store).record(a_date_night(**UNDATED))

    # Assert
    assert store.get_setting("planning.declined:date-night") is None


def test_a_decline_is_stored_under_the_item_id_with_the_date_in_iso_format() -> None:
    # Setup
    store = FreshStore()

    # Execute
    Declines(store).record(a_date_night())

    # Assert
    assert store.get_setting("planning.declined:date-night") == DATE_NIGHT_ON.isoformat()
