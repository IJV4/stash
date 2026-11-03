from datetime import timedelta

import pytest
from builders import BASE, NAIVE, a_capture, an_item

from stash.capture import BurstCoalescer, Deferred, Filed, reply_for, summary

WINDOW_SECONDS = 5.0
WINDOW = timedelta(seconds=WINDOW_SECONDS)


def a_filed(title: str = "Ramen") -> Filed:
    return Filed(an_item(title=title), unsure=False)


def test_a_negative_window_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="window_seconds must not be negative"):
        BurstCoalescer(-1.0)


def test_nothing_is_due_when_nothing_was_added() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW * 10) is None


def test_nothing_is_due_before_the_window_has_passed() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(a_filed(), BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW - timedelta(microseconds=1)) is None


def test_a_single_result_is_due_exactly_when_the_window_has_passed_with_its_normal_reply() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    filed = a_filed()
    bursts.add(filed, BASE)

    # Execute
    reply = bursts.due(BASE + WINDOW)

    # Assert
    assert reply == reply_for(filed)


def test_a_zero_window_makes_a_result_due_immediately() -> None:
    # Setup
    bursts = BurstCoalescer(0)
    filed = a_filed()
    bursts.add(filed, BASE)

    # Execute / Assert
    assert bursts.due(BASE) == reply_for(filed)


def test_three_results_become_one_combined_summary() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    results = [a_filed("One"), a_filed("Two"), a_filed("Three")]
    for result in results:
        bursts.add(result, BASE)

    # Execute
    reply = bursts.due(BASE + WINDOW)

    # Assert
    assert reply == summary(results)


def test_filed_and_deferred_results_are_summarised_together() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    results = [a_filed(), Deferred(a_capture(), "ai_unavailable")]
    for result in results:
        bursts.add(result, BASE)

    # Execute
    reply = bursts.due(BASE + WINDOW)

    # Assert
    assert reply == summary(results)


def test_the_window_runs_from_the_first_result_not_the_last() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    results = [a_filed("One"), a_filed("Two")]
    bursts.add(results[0], BASE)
    bursts.add(results[1], BASE + WINDOW - timedelta(seconds=1))

    # Execute
    reply = bursts.due(BASE + WINDOW)

    # Assert
    assert reply == summary(results)


def test_once_the_reply_is_taken_nothing_more_is_due() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(a_filed(), BASE)
    bursts.due(BASE + WINDOW)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW * 2) is None


def test_the_next_window_starts_at_the_first_result_added_after_the_reply() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(a_filed("Old"), BASE)
    bursts.due(BASE + WINDOW)
    later = BASE + WINDOW * 3
    bursts.add(a_filed("New"), later)

    # Execute / Assert
    assert bursts.due(later + WINDOW - timedelta(seconds=1)) is None


def test_the_next_window_replies_with_only_the_results_added_after_the_previous_reply() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(a_filed("Old"), BASE)
    bursts.due(BASE + WINDOW)
    later = BASE + WINDOW * 3
    fresh = a_filed("New")
    bursts.add(fresh, later)

    # Execute / Assert
    assert bursts.due(later + WINDOW) == reply_for(fresh)


def test_adding_a_result_at_a_naive_time_raises_value_error() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        bursts.add(a_filed(), NAIVE)


def test_asking_what_is_due_at_a_naive_time_raises_value_error() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        bursts.due(NAIVE)


def test_many_results_added_inside_one_window_are_all_summarised() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    count = 8
    for number in range(count):
        bursts.add(a_filed(f"Item {number}"), BASE)

    # Execute
    reply = bursts.due(BASE + WINDOW)

    # Assert
    assert reply is not None
    assert reply.text.startswith(f"✅ Saved {count} items:")


def test_a_batch_whose_reply_cannot_be_built_is_still_held_for_the_next_attempt() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(Filed(an_item(details={"city": "x" * 5000}), unsure=False), BASE)
    with pytest.raises(ValueError, match="reply text exceeds"):
        bursts.due(BASE + WINDOW)

    # Execute / Assert
    with pytest.raises(ValueError, match="reply text exceeds"):
        bursts.due(BASE + WINDOW)
