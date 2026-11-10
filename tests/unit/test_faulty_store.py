from collections.abc import Callable

import pytest
from builders import a_capture
from fakes.faulty_store import FaultyStore, StoreFault

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


def test_a_fault_armed_for_the_next_call_fails_that_call_only() -> None:
    # Setup
    store = FaultyStore()
    store.fail_next("add_capture", StoreFault("c1"))

    # Execute
    with pytest.raises(StoreFault):
        store.add_capture(a_capture())
    added = store.add_capture(a_capture())

    # Assert
    assert added


# a real method rides along so stopping at the first key, or letting it excuse the rest, goes red
ARMING_ROUTES = {
    "fail_on": lambda name, error: FaultyStore(fail_on={"add_capture": error, name: error}),
    "fail_once": lambda name, error: FaultyStore(fail_once={"add_capture": error, name: error}),
    "fail_next": lambda name, error: FaultyStore().fail_next(name, error),
}


@pytest.mark.parametrize("name", ["add_captur", "__init__"])
@pytest.mark.parametrize("arm", ARMING_ROUTES.values(), ids=ARMING_ROUTES.keys())
def test_a_fault_armed_under_a_name_that_is_not_a_public_store_method_raises_value_error_naming_it(
    arm: Callable[[str, BaseException], object], name: str
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=name):
        arm(name, StoreBusyError())
