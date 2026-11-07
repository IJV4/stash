from datetime import UTC, date, datetime, timedelta

from builders import stored
from fakes.fake_step_proposals import FakeStepProposals
from fakes.memory_store import MemoryStore
from planning_builders import DATE_NIGHT_ID, DATE_NIGHT_ON, a_date_night
from planning_rig import planning_over
from step_builders import a_step

from stash.domain import Item, Stage
from stash.planning import Planning

NOON_ON_THE_DATE = datetime(2027, 2, 12, 12, 0, tzinfo=UTC)
UTC_TOMORROW_STILL_TODAY_IN_LOS_ANGELES = datetime(2027, 2, 13, 3, 0, tzinfo=UTC)


def planning_for(store: MemoryStore, now: datetime = NOON_ON_THE_DATE) -> Planning:
    return planning_over(store, FakeStepProposals(), lambda: now)


def with_steps(store: MemoryStore, *, confirmed: bool) -> None:
    store.save_steps(DATE_NIGHT_ID, [a_step(item_id=DATE_NIGHT_ID, confirmed=confirmed)])


def needs_proposal(
    item: Item, *, confirmed_steps: bool | None = None, now: datetime = NOON_ON_THE_DATE
) -> bool:
    store = MemoryStore()
    stored(store, item)
    if confirmed_steps is not None:
        with_steps(store, confirmed=confirmed_steps)
    return planning_for(store, now).needs_proposal(item)


def test_a_planned_dated_item_without_steps_needs_a_proposal() -> None:
    # Setup
    item = a_date_night()

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is True


def test_a_planned_dated_item_with_unconfirmed_steps_does_not() -> None:
    # Setup
    item = a_date_night()

    # Execute
    needed = needs_proposal(item, confirmed_steps=False)

    # Assert
    assert needed is False


def test_a_planned_dated_item_with_confirmed_steps_does_not() -> None:
    # Setup
    item = a_date_night()

    # Execute
    needed = needs_proposal(item, confirmed_steps=True)

    # Assert
    assert needed is False


def test_a_want_to_item_with_a_date_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.WANT_TO)

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_a_want_to_item_without_a_date_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.WANT_TO, date=None)

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_a_doing_item_with_a_date_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.DOING)

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_a_done_item_with_a_date_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.DONE)

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_a_dropped_item_with_a_date_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.DROPPED, date=date(2027, 2, 12))

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_an_inbox_item_does_not() -> None:
    # Setup
    item = a_date_night(stage=Stage.INBOX)

    # Execute
    needed = needs_proposal(item)

    # Assert
    assert needed is False


def test_a_planned_item_dated_yesterday_does_not() -> None:
    # Setup
    item = a_date_night()

    # Execute
    needed = needs_proposal(item, now=NOON_ON_THE_DATE + timedelta(days=1))

    # Assert
    assert needed is False


def test_a_planned_item_dated_today_in_the_configured_time_zone_does() -> None:
    # Setup
    item = a_date_night(date=DATE_NIGHT_ON)

    # Execute
    needed = needs_proposal(item, now=UTC_TOMORROW_STILL_TODAY_IN_LOS_ANGELES)

    # Assert
    assert needed is True
