from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from builders import BASE
from capture_builders import sequential_ids

from stash.lifecycle import Lifecycle
from stash.store import Store

LOCAL_ZONE = ZoneInfo("America/Los_Angeles")


def a_lifecycle(
    store: Store,
    clock: Callable[[], datetime] = lambda: BASE,
    new_id: Callable[[], str] | None = None,
) -> Lifecycle:
    return Lifecycle(store, new_id or sequential_ids(), clock, LOCAL_ZONE)
