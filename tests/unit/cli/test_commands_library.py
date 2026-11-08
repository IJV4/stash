import io

from builders import stored_item
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.cli.commands import show


def test_show_exits_0() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="trip", title="Japan trip")

    # Execute
    exit_code = show(a_lifecycle(store), "trip", io.StringIO())

    # Assert
    assert exit_code == 0
