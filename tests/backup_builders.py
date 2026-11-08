from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fakes.store_factories import FreshStore

from stash.store.backup import Backups, BackupSettings
from stash.store.port import BackupSource

BACKED_UP_AT = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def a_backups(
    source: BackupSource,
    settings: BackupSettings | None = None,
    clock: Callable[[], datetime] = lambda: BACKED_UP_AT,
    **options: Any,
) -> Backups:
    return Backups(source, FreshStore() if settings is None else settings, clock, **options)
