from datetime import timedelta

import pytest
from builders import BASE, NAIVE, a_capture, an_item

from stash.capture import BurstCoalescer, Deferred, Filed, reply_for, summary

WINDOW_SECONDS = 5.0
WINDOW = timedelta(seconds=WINDOW_SECONDS)


def a_filed(title: str = "Ramen") -> Filed:
    return Filed(an_item(id=f"item-{title.replace(' ', '-')}", title=title), unsure=False)


def a_deferred(capture_id: str = "c1") -> Deferred:
    return Deferred(a_capture(id=capture_id), "ai_unavailable")


def test_a_negative_window_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="window_seconds must not be negative"):
        BurstCoalescer(-1.0)


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


def test_a_batch_whose_reply_cannot_be_built_is_still_held_for_the_next_attempt() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    bursts.add(Filed(an_item(details={"city": "x" * 5000}), unsure=False), BASE)
    with pytest.raises(ValueError, match="reply text exceeds"):
        bursts.due(BASE + WINDOW)

    # Execute / Assert
    with pytest.raises(ValueError, match="reply text exceeds"):
        bursts.due(BASE + WINDOW)


def test_adding_the_same_filed_item_twice_keeps_the_single_item_reply() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    filed = a_filed()
    bursts.add(filed, BASE)
    bursts.add(filed, BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == reply_for(filed)


def test_adding_the_same_deferred_capture_twice_keeps_the_single_capture_reply() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    deferred = a_deferred()
    bursts.add(deferred, BASE)
    bursts.add(deferred, BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == reply_for(deferred)


def test_a_duplicate_does_not_restart_the_window() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    filed = a_filed()
    bursts.add(filed, BASE)
    bursts.add(filed, BASE + WINDOW - timedelta(seconds=1))

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == reply_for(filed)


def test_a_duplicate_is_ignored_among_other_results_of_the_batch() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    first, second = a_filed("One"), a_filed("Two")
    for result in (first, second, first):
        bursts.add(result, BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == summary([first, second])


def test_a_filed_item_and_a_deferred_capture_with_the_same_id_are_both_kept() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    results: list[Filed | Deferred] = [Filed(an_item(id="same"), unsure=False), a_deferred("same")]
    for result in results:
        bursts.add(result, BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == summary(results)


def test_two_deferred_captures_with_different_ids_are_both_kept() -> None:
    # Setup
    bursts = BurstCoalescer(WINDOW_SECONDS)
    results: list[Filed | Deferred] = [a_deferred("c1"), a_deferred("c2")]
    for result in results:
        bursts.add(result, BASE)

    # Execute / Assert
    assert bursts.due(BASE + WINDOW) == summary(results)
