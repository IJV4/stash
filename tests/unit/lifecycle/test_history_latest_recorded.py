from datetime import timedelta

from builders import COMPLETED_ON, an_item, an_outcome, minutes_after

from stash.lifecycle import ItemHistory


def test_the_latest_recorded_outcome_is_the_one_recorded_most_recently() -> None:
    # Setup
    older = an_outcome(id="o1", recorded_at=minutes_after(0))
    newer = an_outcome(id="o2", recorded_at=minutes_after(5))
    history = ItemHistory(an_item(), (newer, older), ())

    # Execute
    latest = history.latest_recorded

    # Assert
    assert latest == newer


def test_the_latest_recorded_outcome_ignores_the_completion_date() -> None:
    # Setup
    recorded_last = an_outcome(id="o1", recorded_at=minutes_after(5))
    completed_last = an_outcome(
        id="o2", recorded_at=minutes_after(0), completed_on=COMPLETED_ON + timedelta(days=1)
    )
    history = ItemHistory(an_item(), (completed_last, recorded_last), ())

    # Execute
    latest = history.latest_recorded

    # Assert
    assert latest == recorded_last


def test_a_history_without_outcomes_has_no_latest_recorded_outcome() -> None:
    # Setup
    history = ItemHistory(an_item(), (), ())

    # Execute
    latest = history.latest_recorded

    # Assert
    assert latest is None
