from datetime import timedelta

from fakes.memory_store import MemoryStore

from stash.gpu.override import ManualOverride

FOUR_HOURS = timedelta(hours=4)


def an_override(
    store: MemoryStore | None = None, duration: timedelta = FOUR_HOURS
) -> ManualOverride:
    return ManualOverride(MemoryStore() if store is None else store, duration)
