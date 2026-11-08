from collections.abc import Callable

import pytest
from app_builders import an_app
from fakes.close_counter import CloseCounter

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
