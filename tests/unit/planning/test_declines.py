from fakes.store_factories import FreshStore
from planning_builders import a_date_night

from stash.domain import Stage
from stash.planning.declines import Declines

UNDATED = {"stage": Stage.WANT_TO, "date": None}


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
