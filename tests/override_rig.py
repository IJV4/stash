from datetime import timedelta

from fakes.store_factories import FreshStore

from stash.gpu.override import ManualOverride

FOUR_HOURS = timedelta(hours=4)


def an_override(
    store: FreshStore | None = None, duration: timedelta = FOUR_HOURS
) -> ManualOverride:
    return ManualOverride(FreshStore() if store is None else store, duration)
