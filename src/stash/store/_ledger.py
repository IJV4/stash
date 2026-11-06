import sqlite3
import threading
from datetime import datetime

from stash.domain import Nudge, NudgeKey, NudgeKind, require_aware, utc_text
from stash.store import _sql as sql


class SqliteLedger:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def was_sent(self, key: NudgeKey) -> bool:
        with self._lock:
            return self._connection.execute(sql.NUDGE_WAS_SENT, key).fetchone() is not None

    def record_sent(self, nudge: Nudge, sent_at: datetime) -> bool:
        require_aware("sent_at", sent_at)
        with self._lock:
            inserted = self._connection.execute(
                sql.INSERT_SENT_NUDGE, (*nudge.key, utc_text(sent_at))
            )
        return inserted.rowcount == 1

    def last_sent(self, kind: NudgeKind) -> datetime | None:
        with self._lock:
            latest = self._connection.execute(sql.LAST_SENT, (kind.value,)).fetchone()["latest"]
        return None if latest is None else datetime.fromisoformat(latest)
