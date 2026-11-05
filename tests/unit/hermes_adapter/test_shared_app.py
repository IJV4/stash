import logging
from collections.abc import Callable

import pytest
from app_builders import an_app
from fakes.close_counter import CloseCounter
from log_records import recording_logs

from stash.app import StashApp
from stash.hermes_adapter.plugin import SharedApp

LOGGER = "stash.hermes_adapter.plugin"


class CountingOpener:
    def __init__(self, failure: Exception | None = None) -> None:
        self.opened: list[StashApp] = []
        self._failure = failure

    def __call__(self) -> StashApp:
        if self._failure is not None:
            raise self._failure
        app = an_app(resources=CloseCounter())
        self.opened.append(app)
        return app


def test_the_first_open_builds_the_app_with_the_opener() -> None:
    # Setup
    opener = CountingOpener()

    # Execute
    app = SharedApp().open_once(opener, [].append)

    # Assert
    assert opener.opened == [app]


def test_the_first_open_registers_the_close_of_the_app_with_the_exit_hook() -> None:
    # Setup
    resources = CloseCounter()
    exits: list[Callable[[], None]] = []

    # Execute
    SharedApp().open_once(lambda: an_app(resources=resources), exits.append)
    for close in exits:
        close()

    # Assert
    assert resources.closes == 1


def test_a_later_open_returns_the_app_the_first_open_built() -> None:
    # Setup
    shared = SharedApp()
    first = shared.open_once(CountingOpener(), [].append)

    # Execute
    again = shared.open_once(CountingOpener(), [].append)

    # Assert
    assert again is first


def test_a_later_open_does_not_call_its_opener() -> None:
    # Setup
    shared = SharedApp()
    shared.open_once(CountingOpener(), [].append)
    later = CountingOpener()

    # Execute
    shared.open_once(later, [].append)

    # Assert
    assert later.opened == []


def test_a_later_open_registers_no_second_exit_hook() -> None:
    # Setup
    shared = SharedApp()
    exits: list[Callable[[], None]] = []
    shared.open_once(CountingOpener(), exits.append)

    # Execute
    shared.open_once(CountingOpener(), exits.append)

    # Assert
    assert len(exits) == 1


def test_a_later_open_logs_one_info_line_about_restarting_to_reload_the_configuration() -> None:
    # Setup
    shared = SharedApp()
    shared.open_once(CountingOpener(), [].append)

    # Execute
    with recording_logs(LOGGER) as logs:
        shared.open_once(CountingOpener(), [].append)

    # Assert
    assert logs.entries() == [
        (logging.INFO, "reusing the open stash app; restart the gateway to reload stash.toml")
    ]


def test_the_first_open_logs_nothing() -> None:
    # Execute
    with recording_logs(LOGGER) as logs:
        SharedApp().open_once(CountingOpener(), [].append)

    # Assert
    assert logs.entries() == []


def test_an_opener_that_fails_registers_no_exit_hook() -> None:
    # Setup
    exits: list[Callable[[], None]] = []

    # Execute
    with pytest.raises(RuntimeError):
        SharedApp().open_once(CountingOpener(RuntimeError("unreadable")), exits.append)

    # Assert
    assert exits == []


def test_an_open_after_a_failed_open_builds_the_app() -> None:
    # Setup
    shared = SharedApp()
    with pytest.raises(RuntimeError):
        shared.open_once(CountingOpener(RuntimeError("unreadable")), [].append)
    opener = CountingOpener()

    # Execute
    app = shared.open_once(opener, [].append)

    # Assert
    assert opener.opened == [app]


def test_an_exit_hook_that_fails_leaves_no_app_cached() -> None:
    # Setup
    shared = SharedApp()

    def failing_exit_hook(close: Callable[[], None]) -> None:
        raise RuntimeError("no exit hook available")

    with pytest.raises(RuntimeError):
        shared.open_once(CountingOpener(), failing_exit_hook)
    opener = CountingOpener()

    # Execute
    app = shared.open_once(opener, [].append)

    # Assert
    assert opener.opened == [app]
