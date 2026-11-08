import logging
from datetime import timedelta

import pytest
from builders import BASE
from fakes.store_factories import FreshStore
from override_rig import an_override

A_YEAR_AND_A_DAY = timedelta(days=366)


def test_a_stored_value_that_is_not_a_timestamp_is_inactive() -> None:
    # Setup
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_timestamp_without_an_offset_is_inactive() -> None:
    # Setup
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "2026-11-02T16:00:00")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_value_that_is_not_a_timestamp_is_logged_as_a_warning_naming_the_setting(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    store = FreshStore()
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
    store = FreshStore()
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
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert "next tuesday" not in caplog.text


def test_a_stored_expiry_far_beyond_any_switch_off_is_inactive() -> None:
    # Setup
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")

    # Execute
    until = an_override(store).active_until(BASE)

    # Assert
    assert until is None


def test_a_stored_expiry_one_second_beyond_a_year_and_a_day_ahead_is_inactive() -> None:
    # Setup
    store = FreshStore()
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
    store = FreshStore()
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
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")

    # Execute
    an_override(store).active_until(BASE)

    # Assert
    assert "9999" not in caplog.text
