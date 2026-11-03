from typing import cast

import pytest
from builders import a_capture, an_item

from stash.capture.replies import (
    TELEGRAM_TEXT_LIMIT,
    confirmation,
    deferred,
    reply_for,
    summary,
)
from stash.capture.results import Deferred, Duplicate, Filed
from stash.domain import ItemType


def a_filed(title: str, item_type: ItemType = ItemType.PLACE, unsure: bool = False) -> Filed:
    return Filed(an_item(title=title, item_type=item_type), unsure=unsure)


def test_the_reply_for_a_filed_result_is_its_confirmation() -> None:
    # Setup
    filed = a_filed("Ramen")

    # Execute / Assert
    assert reply_for(filed) == confirmation(filed.item, False)


def test_the_reply_for_an_unsure_filed_result_carries_the_question_button() -> None:
    # Setup
    filed = a_filed("Ramen", unsure=True)

    # Execute / Assert
    assert reply_for(filed) == confirmation(filed.item, True)


def test_the_reply_for_a_deferred_result_is_the_deferred_notice_for_its_reason() -> None:
    # Setup
    result = Deferred(a_capture(), "gpu_busy")

    # Execute / Assert
    assert reply_for(result) == deferred("gpu_busy")


def test_a_summary_counts_the_items_and_lists_one_bullet_per_filed_item() -> None:
    # Setup
    results = [
        a_filed("Ichiran ramen"),
        a_filed("Dune", ItemType.BOOK),
        a_filed("Sell candles", ItemType.IDEA),
    ]

    # Execute
    reply = summary(results)

    # Assert
    assert reply.text == (
        "✅ Saved 3 items:\n• Places · Ichiran ramen\n• Books · Dune\n• Ideas · Sell candles"
    )


def test_a_summary_lists_a_deferred_capture_by_its_derived_title_as_not_filed_yet() -> None:
    # Setup
    results = [
        a_filed("Dune", ItemType.BOOK),
        Deferred(a_capture(text="Ramen\nnext line"), "gpu_busy"),
    ]

    # Execute
    reply = summary(results)

    # Assert
    assert reply.text.splitlines()[2] == "• 📥 Ramen (not filed yet)"


def test_a_summary_has_no_buttons_even_when_a_result_was_unsure() -> None:
    # Execute
    reply = summary([a_filed("Ramen", unsure=True), a_filed("Dune")])

    # Assert
    assert reply.buttons == ()


def test_a_summary_of_many_long_titles_never_exceeds_the_telegram_limit() -> None:
    # Setup
    results = [a_filed("x" * 120) for _ in range(200)]

    # Execute
    reply = summary(results)

    # Assert
    assert len(reply.text) <= TELEGRAM_TEXT_LIMIT


def test_a_truncated_summary_keeps_the_total_in_its_header() -> None:
    # Execute
    reply = summary([a_filed("x" * 120) for _ in range(200)])

    # Assert
    assert reply.text.startswith("✅ Saved 200 items:\n")


def test_a_truncated_summary_ends_by_counting_exactly_the_bullets_it_left_out() -> None:
    # Execute
    lines = summary([a_filed("x" * 120) for _ in range(200)]).text.splitlines()

    # Assert
    shown = len(lines) - 2
    assert lines[-1] == f"• …and {200 - shown} more"


def test_a_summary_that_just_fits_is_not_truncated() -> None:
    # Setup
    header_and_newline = len("✅ Saved 2 items:\n")
    bullet = "• Places · "
    room = TELEGRAM_TEXT_LIMIT - header_and_newline - 1 - 2 * len(bullet)
    results = [a_filed("a" * (room // 2)), a_filed("b" * (room - room // 2))]

    # Execute
    reply = summary(results)

    # Assert
    assert len(reply.text) == TELEGRAM_TEXT_LIMIT


def test_a_summary_one_character_too_long_is_truncated_with_a_tail() -> None:
    # Setup
    header_and_newline = len("✅ Saved 2 items:\n")
    bullet = "• Places · "
    room = TELEGRAM_TEXT_LIMIT - header_and_newline - 1 - 2 * len(bullet) + 1
    results = [a_filed("a" * (room // 2)), a_filed("b" * (room - room // 2))]

    # Execute
    reply = summary(results)

    # Assert
    assert reply.text.endswith("• …and 1 more")


def three_results_whose_first_two_bullets_total(length: int) -> list[Filed]:
    room = length - 2 * len("• Places · ")
    return [a_filed("a" * (room // 2)), a_filed("b" * (room - room // 2)), a_filed("c" * 200)]


def test_a_truncated_summary_whose_tail_ends_exactly_at_the_limit_keeps_both_bullets() -> None:
    # Setup
    tail_and_separators = len("✅ Saved 3 items:") + 3 + len("• …and 1 more")
    results = three_results_whose_first_two_bullets_total(TELEGRAM_TEXT_LIMIT - tail_and_separators)

    # Execute
    reply = summary(results)

    # Assert
    assert (len(reply.text), reply.text.endswith("• …and 1 more")) == (TELEGRAM_TEXT_LIMIT, True)


def test_a_truncated_summary_whose_tail_would_pass_the_limit_by_one_drops_the_second_bullet() -> (
    None
):
    # Setup
    tail_and_separators = len("✅ Saved 3 items:") + 3 + len("• …and 1 more")
    results = three_results_whose_first_two_bullets_total(
        TELEGRAM_TEXT_LIMIT - tail_and_separators + 1
    )

    # Execute
    reply = summary(results)

    # Assert
    assert reply.text.endswith("• …and 2 more")


def test_a_result_that_is_neither_filed_nor_deferred_is_refused_by_reply_for() -> None:
    # Execute / Assert
    with pytest.raises(AssertionError):
        reply_for(cast("Filed", Duplicate()))


def test_a_result_that_is_neither_filed_nor_deferred_is_refused_by_summary() -> None:
    # Execute / Assert
    with pytest.raises(AssertionError):
        summary([cast("Filed", Duplicate())])
