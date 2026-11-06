from datetime import UTC, datetime

from stash.domain._validation import require_aware


def utc_text(moment: datetime) -> str:
    require_aware("moment", moment)
    return moment.astimezone(UTC).isoformat(timespec="microseconds")
