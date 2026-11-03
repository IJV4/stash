import logging
from datetime import timedelta

import pytest
from builders import BASE, PLUS_FIVE
from fakes.memory_store import MemoryStore
from override_rig import an_override

A_YEAR_AND_A_DAY = timedelta(days=366)


def test_expiry_is_stored_under_the_manual_off_setting_as_utc_iso_8601() -> None:
    # Setup
    store = MemoryStore()
    override = an_override(store)

    # Execute
    override.off(BASE.astimezone(PLUS_FIVE))

    # Assert
    assert store.get_setting("gpu.manual_off_until") == "2026-11-02T16:00:00+00:00"


def test_turning_on_stores_an_empty_value_under_the_manual_off_setting() -> None:
    # Setup
    store = MemoryStore()
    override = an_override(store)
    override.off(BASE)

    # Execute
    override.on()

    # Assert
    assert store.get_setting("gpu.manual_off_until") == ""


def test_a_new_override_on_the_same_store_sees_the_active_expiry() -> None:
    # Setup
    store = MemoryStore()
    expiry = an_override(store).off(BASE)

    # Execute
    until = an_override(store).active_until(BASE + timedelta(hours=1))

    # Assert
    assert until == expiry


def test_a_new_override_on_the_same_store_sees_that_it_was_turned_on() -> None:
    # Setup
    store = MemoryStore()
    first = an_override(store)
    first.off(BASE)
    first.on()

    # Execute
    until = an_override(store).active_until(BASE + timedelta(hours=1))

    # Assert
    assert until is None


def test_a_stored_value_that_is_not_a_timestamp_is_inactive() -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_timestamp_without_an_offset_is_inactive() -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "2026-11-02T16:00:00")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_value_that_is_not_a_timestamp_is_logged_as_a_warning_naming_the_setting(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert [(r.levelno, "gpu.manual_off_until" in r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, True)
    ]


def test_a_stored_timestamp_without_an_offset_is_logged_as_a_warning_naming_the_setting(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "2026-11-02T16:00:00")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert [(r.levelno, "gpu.manual_off_until" in r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, True)
    ]


def test_the_warning_for_a_corrupt_value_does_not_repeat_the_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert "next tuesday" not in caplog.text


def test_a_valid_stored_value_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    # Setup
    override = an_override()
    override.off(BASE)

    # Execute
    override.active_until(BASE)

    # Assert
    assert caplog.records == []


def test_a_stored_expiry_far_beyond_any_switch_off_is_inactive() -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_expiry_exactly_a_year_and_a_day_ahead_is_still_active() -> None:
    # Setup
    store = MemoryStore()
    expiry = BASE + A_YEAR_AND_A_DAY
    store.put_setting("gpu.manual_off_until", expiry.isoformat())

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until == expiry


def test_a_stored_expiry_one_second_beyond_a_year_and_a_day_ahead_is_inactive() -> None:
    # Setup
    store = MemoryStore()
    store.put_setting(
        "gpu.manual_off_until", (BASE + A_YEAR_AND_A_DAY + timedelta(seconds=1)).isoformat()
    )

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_expiry_far_beyond_any_switch_off_is_logged_as_a_warning_naming_the_setting(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert [(r.levelno, "gpu.manual_off_until" in r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, True)
    ]


def test_the_warning_for_a_far_future_expiry_does_not_repeat_the_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert "9999" not in caplog.text
