import pytest
from builders import a_capture
from fakes.faulty_store import FaultyStore

from stash.store import StoreBusyError


def test_a_configured_method_raises_the_given_exception() -> None:
    # Setup
    store = FaultyStore(fail_on={"add_capture": StoreBusyError()})

    # Execute / Assert
    with pytest.raises(StoreBusyError):
        store.add_capture(a_capture())


def test_an_unconfigured_method_answers_like_the_real_store() -> None:
    # Setup
    store = FaultyStore(fail_on={"save_item": StoreBusyError()})
    capture = a_capture()

    # Execute
    store.add_capture(capture)

    # Assert
    assert store.get_capture(capture.id) == capture


def test_a_fault_removed_from_fail_on_stops_failing() -> None:
    # Setup
    store = FaultyStore(fail_on={"add_capture": StoreBusyError()})
    del store.fail_on["add_capture"]

    # Execute
    added = store.add_capture(a_capture())

    # Assert
    assert added


def test_recorded_calls_list_the_store_methods_in_order() -> None:
    # Setup
    store = FaultyStore(record=True)
    capture = a_capture()

    # Execute
    store.add_capture(capture)
    store.get_capture(capture.id)

    # Assert
    assert store.calls == ["add_capture", "get_capture"]
