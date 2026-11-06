from datetime import date

from builders import in_los_angeles
from nudge_builders import SUNDAY, a_nudge_schedule

DIGEST_INSTANT = in_los_angeles(SUNDAY, 10)


def test_the_forgotten_cutoff_is_the_configured_number_of_days_before_the_instant() -> None:
    # Execute
    cutoff = a_nudge_schedule(forgotten_after_days=7).forgotten_cutoff(DIGEST_INSTANT)

    # Assert
    assert cutoff == in_los_angeles(date(2027, 2, 7), 10)
