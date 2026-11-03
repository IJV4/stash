from datetime import timedelta

import pytest
from builders import BASE, NAIVE, PLUS_FIVE
from override_rig import FOUR_HOURS, an_override


def test_override_that_was_never_turned_off_is_inactive() -> None:
    # Setup
    override = an_override()

    # Execute
    until = override.active_until(BASE)

    # Assert
    assert until is None


def test_turning_off_returns_the_expiry_one_duration_from_now() -> None:
    # Setup
    override = an_override()

    # Execute
    expiry = override.off(BASE)

    # Assert
    assert expiry == BASE + FOUR_HOURS


def test_turning_off_uses_the_configured_duration() -> None:
    # Setup
    override = an_override(duration=timedelta(minutes=90))

    # Execute
    expiry = override.off(BASE)

    # Assert
    assert expiry == BASE + timedelta(minutes=90)


def test_turned_off_override_is_active_until_the_expiry() -> None:
    # Setup
    override = an_override()
    expiry = override.off(BASE)

    # Execute
    until = override.active_until(BASE + timedelta(hours=1))

    # Assert
    assert until == expiry


def test_override_is_still_active_one_second_before_the_expiry() -> None:
    # Setup
    override = an_override()
    expiry = override.off(BASE)

    # Execute
    until = override.active_until(expiry - timedelta(seconds=1))

    # Assert
    assert until == expiry


def test_override_is_inactive_exactly_at_the_expiry() -> None:
    # Setup
    override = an_override()
    expiry = override.off(BASE)

    # Execute
    until = override.active_until(expiry)

    # Assert
    assert until is None


def test_override_is_inactive_after_the_expiry() -> None:
    # Setup
    override = an_override()
    expiry = override.off(BASE)

    # Execute
    until = override.active_until(expiry + timedelta(seconds=1))

    # Assert
    assert until is None


def test_turning_on_cancels_an_active_override() -> None:
    # Setup
    override = an_override()
    override.off(BASE)

    # Execute
    override.on()

    # Assert
    assert override.active_until(BASE + timedelta(minutes=1)) is None


def test_turning_off_again_replaces_the_previous_expiry() -> None:
    # Setup
    override = an_override()
    override.off(BASE)
    later = BASE + timedelta(hours=3)

    # Execute
    expiry = override.off(later)

    # Assert
    assert override.active_until(later) == expiry == later + FOUR_HOURS


def test_expiry_is_compared_as_an_instant_across_timezones() -> None:
    # Setup
    override = an_override()
    expiry = override.off(BASE)
    just_before = (expiry - timedelta(seconds=1)).astimezone(PLUS_FIVE)

    # Execute
    until = override.active_until(just_before)

    # Assert
    assert until == expiry


def test_turning_off_with_a_naive_now_raises_value_error() -> None:
    # Setup
    override = an_override()

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        override.off(NAIVE)


def test_checking_with_a_naive_now_raises_value_error() -> None:
    # Setup
    override = an_override()

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        override.active_until(NAIVE)


def test_a_zero_duration_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="duration"):
        an_override(duration=timedelta(0))


def test_a_negative_duration_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="duration"):
        an_override(duration=timedelta(hours=-1))
