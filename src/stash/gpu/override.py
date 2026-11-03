import logging
from datetime import UTC, datetime, timedelta

from stash.domain import require_aware
from stash.store.port import SettingsStore

logger = logging.getLogger(__name__)

MANUAL_OFF_KEY = "gpu.manual_off_until"
SWITCHED_ON = ""
MAX_SWITCH_OFF = timedelta(days=366)


def _ignore_corrupt() -> None:
    logger.warning("ignoring %s: stored value is not a usable switch-off expiry", MANUAL_OFF_KEY)


def _parse_expiry(stored: str, now: datetime) -> datetime | None:
    try:
        expiry = datetime.fromisoformat(stored)
        require_aware(MANUAL_OFF_KEY, expiry)
    except ValueError:
        _ignore_corrupt()
        return None
    if expiry - now > MAX_SWITCH_OFF:
        _ignore_corrupt()
        return None
    return expiry


class ManualOverride:
    def __init__(self, store: SettingsStore, duration: timedelta) -> None:
        if duration <= timedelta(0):
            raise ValueError(f"duration must be positive, got {duration}")
        self._store = store
        self._duration = duration

    def off(self, now: datetime) -> datetime:
        require_aware("now", now)
        expiry = now + self._duration
        self._store.put_setting(MANUAL_OFF_KEY, expiry.astimezone(UTC).isoformat())
        return expiry

    def on(self) -> None:
        self._store.put_setting(MANUAL_OFF_KEY, SWITCHED_ON)

    def active_until(self, now: datetime) -> datetime | None:
        require_aware("now", now)
        stored = self._store.get_setting(MANUAL_OFF_KEY)
        if not stored:
            return None
        expiry = _parse_expiry(stored, now)
        return expiry if expiry is not None and now < expiry else None
