from datetime import UTC, datetime, timedelta

import pytest
from builders import a_capture, a_source
from fakes.search_path import FakeSearchPath
from fakes.store_factories import FreshStore

from stash.doctor_probes import (
    BackupProbe,
    ExecutableProbe,
    PendingCapturesProbe,
)
from stash.llm import ProbeResult
from stash.store import BACKUP_LAST_SUCCESS_KEY

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def test_the_executable_probe_passes_with_the_path_where_it_was_found() -> None:
    # Setup
    probe = ExecutableProbe("deno", FakeSearchPath({"deno": "/usr/bin/deno"}), "a hint")

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "/usr/bin/deno")


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (timedelta(minutes=59), ProbeResult(True, "last success 0 hours ago")),
        (timedelta(hours=1), ProbeResult(True, "last success 1 hour ago")),
        (timedelta(hours=47, minutes=59), ProbeResult(True, "last success 47 hours ago")),
        (timedelta(hours=48), ProbeResult(False, "last success 2 days ago")),
        (timedelta(days=3, hours=23), ProbeResult(False, "last success 3 days ago")),
    ],
    ids=["under-an-hour", "one-hour", "just-inside-48h", "exactly-48h", "whole-days-only"],
)
def test_the_backup_probe_passes_under_48_hours_and_fails_from_48_hours_naming_the_age(
    age: timedelta, expected: ProbeResult
) -> None:
    # Setup
    settings = FreshStore()
    settings.put_setting(BACKUP_LAST_SUCCESS_KEY, (NOW - age).isoformat())

    # Execute
    result = BackupProbe(settings, lambda: NOW).check()

    # Assert
    assert result == expected


def test_the_pending_captures_probe_names_the_count_and_the_oldest_day_but_not_the_text() -> None:
    # Setup
    store = FreshStore()
    store.add_capture(a_capture(id="c1", received_at=NOW, text="secret words"))
    store.add_capture(
        a_capture(id="c2", source=a_source("m2"), received_at=NOW - timedelta(days=3), text="more")
    )

    # Execute
    result = PendingCapturesProbe(store).check()

    # Assert
    assert result == ProbeResult(
        False, "2 saved but not filed, oldest 2026-11-02; run: stash retry"
    )
