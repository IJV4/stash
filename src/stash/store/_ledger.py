import sqlite3
import threading
from collections.abc import Sequence
from datetime import datetime

from stash.domain import Nudge, NudgeKey, NudgeKind, require_aware, utc_text
from stash.store import _sql as sql
from stash.store._transaction import immediate_transaction


class SqliteLedger:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def was_sent(self, key: NudgeKey) -> bool:
        with self._lock:
            return self._connection.execute(sql.NUDGE_WAS_SENT, key).fetchone() is not None

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool:
        require_aware("sent_at", sent_at)
        sent_text = utc_text(sent_at)
        with self._lock, immediate_transaction(self._connection):
            inserted = [
                self._connection.execute(sql.INSERT_SENT_NUDGE, (*nudge.key, sent_text)).rowcount
                for nudge in nudges
            ]
        return all(count == 1 for count in inserted)

    def last_sent(self, kind: NudgeKind) -> datetime | None:
        with self._lock:
            latest = self._connection.execute(sql.LAST_SENT, (kind.value,)).fetchone()["latest"]
        return None if latest is None else datetime.fromisoformat(latest)
