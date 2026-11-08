import pytest
from builders import BASE, LATER, NAIVE, PLUS_FIVE
from fakes.store_factories import StoreFactory, on_sqlite
from step_builders import a_nudge

from stash.domain import Nudge, NudgeKind


def two_new_nudges() -> list[Nudge]:
    return [
        a_nudge(kind=NudgeKind.STEP, subject_id="s1"),
        a_nudge(kind=NudgeKind.ITEM_DATE, subject_id="d1"),
    ]


@on_sqlite
def test_recording_nudges_that_were_all_new_reports_that_all_were_recorded(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        # Execute
        recorded_all = store.record_all_sent(two_new_nudges(), BASE)

        # Assert
        assert recorded_all is True


@on_sqlite
def test_recording_nudges_that_were_all_new_marks_every_one_as_sent(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        nudges = two_new_nudges()

        # Execute
        store.record_all_sent(nudges, BASE)

        # Assert
        assert [store.was_sent(nudge.key) for nudge in nudges] == [True, True]


@on_sqlite
def test_recording_nudges_when_one_was_already_recorded_reports_false(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        nudges = two_new_nudges()
        store.record_all_sent([nudges[0]], BASE)

        # Execute
        recorded_all = store.record_all_sent(nudges, LATER)

        # Assert
        assert recorded_all is False


@on_sqlite
def test_recording_nudges_when_one_was_already_recorded_still_records_the_others(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        nudges = two_new_nudges()
        store.record_all_sent([nudges[0]], BASE)

        # Execute
        store.record_all_sent(nudges, LATER)

        # Assert
        assert store.was_sent(nudges[1].key) is True


@on_sqlite
def test_a_nudge_that_was_already_recorded_keeps_its_original_send_time(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        nudges = two_new_nudges()
        store.record_all_sent([nudges[0]], BASE)
        store.record_all_sent(nudges, LATER)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last == BASE


@on_sqlite
def test_recording_the_same_nudge_twice_in_one_call_reports_false(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        # Execute
        recorded_all = store.record_all_sent([a_nudge(), a_nudge()], BASE)

        # Assert
        assert recorded_all is False


@on_sqlite
def test_recording_no_nudges_reports_that_all_were_recorded(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        recorded_all = store.record_all_sent([], BASE)

        # Assert
        assert recorded_all is True


@on_sqlite
def test_recording_no_nudges_records_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_all_sent([], BASE)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last is None


@on_sqlite
def test_recording_nudges_with_a_naive_send_time_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="sent_at"):
        # Execute / Assert
        store.record_all_sent(two_new_nudges(), NAIVE)


@on_sqlite
def test_recording_nudges_with_a_naive_send_time_records_none_of_them(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        nudges = two_new_nudges()
        with pytest.raises(ValueError, match="sent_at"):
            store.record_all_sent(nudges, NAIVE)

        # Execute
        sent = [store.was_sent(nudge.key) for nudge in nudges]

        # Assert
        assert sent == [False, False]


@on_sqlite
def test_recording_nudges_with_a_naive_send_time_is_refused_even_when_there_are_none(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="sent_at"):
        # Execute / Assert
        store.record_all_sent([], NAIVE)


@on_sqlite
def test_the_send_time_of_recorded_nudges_is_the_latest_send_time_of_their_kind(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_all_sent(two_new_nudges(), BASE.astimezone(PLUS_FIVE))

        # Execute
        last = store.last_sent(NudgeKind.ITEM_DATE)

        # Assert
        assert last == BASE
