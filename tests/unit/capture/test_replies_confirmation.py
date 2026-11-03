import pytest
from capture_builders import a_placed_item

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT
from stash.capture.replies import (
    DEFERRED_TEXT,
    TELEGRAM_TEXT_LIMIT,
    Button,
    Reply,
    confirmation,
    deferred,
    gone,
)
from stash.capture.results import DeferralReason
from stash.domain import ItemType


def test_a_confirmation_names_the_type_the_city_and_the_stage() -> None:
    # Execute
    reply = confirmation(a_placed_item(details={"city": "Tokyo"}), unsure=False)

    # Assert
    assert reply.text == "✅ Places · Tokyo · Want to"


def test_a_confirmation_falls_back_to_the_author_when_there_is_no_city() -> None:
    # Execute
    reply = confirmation(a_placed_item(details={"author": "Ana"}), unsure=False)

    # Assert
    assert reply.text == "✅ Places · Ana · Want to"


def test_a_confirmation_falls_back_to_the_platform_when_there_is_no_city_or_author() -> None:
    # Execute
    reply = confirmation(a_placed_item(details={"platform": "youtube"}), unsure=False)

    # Assert
    assert reply.text == "✅ Places · youtube · Want to"


def test_a_confirmation_prefers_the_city_over_the_author_and_the_platform() -> None:
    # Setup
    details = {"platform": "youtube", "author": "Ana", "city": "Tokyo"}

    # Execute
    reply = confirmation(a_placed_item(details=details), unsure=False)

    # Assert
    assert reply.text == "✅ Places · Tokyo · Want to"


def test_a_confirmation_skips_a_blank_city() -> None:
    # Execute
    reply = confirmation(a_placed_item(details={"city": "  ", "author": "Ana"}), unsure=False)

    # Assert
    assert reply.text == "✅ Places · Ana · Want to"


def test_a_confirmation_without_any_detail_has_no_detail_segment() -> None:
    # Execute
    reply = confirmation(a_placed_item(item_type=ItemType.IDEA, details={"cuisine": "x"}), False)

    # Assert
    assert reply.text == "✅ Ideas · Want to"


def test_a_sure_confirmation_offers_only_the_type_and_stage_buttons() -> None:
    # Execute
    reply = confirmation(a_placed_item(), unsure=False)

    # Assert
    assert reply.buttons == ((Button("Type", "stash:t:i1"), Button("Stage", "stash:s:i1")),)


def test_an_unsure_confirmation_adds_a_that_was_a_question_row_for_the_capture() -> None:
    # Execute
    reply = confirmation(a_placed_item(), unsure=True)

    # Assert
    assert reply.buttons[1:] == ((Button("That was a question →", "stash:q:c1"),),)


@pytest.mark.parametrize(
    ("reason", "text"),
    [
        ("gpu_busy", "📥 Saved — I'll file it when the GPU is free."),
        ("ai_unavailable", "📥 Saved — I'll file it once the AI is reachable."),
    ],
)
def test_a_deferred_reply_says_the_capture_is_saved_and_why_filing_waits(
    reason: DeferralReason, text: str
) -> None:
    # Execute
    reply = deferred(reason)

    # Assert
    assert reply == Reply(text, ())


def test_the_gone_reply_says_the_item_no_longer_exists_and_has_no_buttons() -> None:
    # Execute / Assert
    assert gone() == Reply("That item no longer exists.", ())


def test_a_button_with_a_blank_label_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="label"):
        Button("  ", "stash:t:i1")


def test_a_button_with_data_over_the_telegram_limit_in_bytes_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="64 bytes"):
        Button("Go", "é" * (TELEGRAM_CALLBACK_LIMIT // 2 + 1))


def test_a_button_with_data_of_exactly_the_telegram_limit_is_accepted() -> None:
    # Execute
    button = Button("Go", "a" * TELEGRAM_CALLBACK_LIMIT)

    # Assert
    assert len(button.data) == TELEGRAM_CALLBACK_LIMIT


def test_a_reply_with_blank_text_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="text"):
        Reply(" \n", ())


def test_a_reply_over_the_telegram_text_limit_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="4096"):
        Reply("x" * (TELEGRAM_TEXT_LIMIT + 1), ())


def test_a_reply_of_exactly_the_telegram_text_limit_is_accepted() -> None:
    # Execute
    reply = Reply("x" * TELEGRAM_TEXT_LIMIT, ())

    # Assert
    assert len(reply.text) == TELEGRAM_TEXT_LIMIT


def test_a_reply_ignores_later_changes_to_the_button_rows_it_was_built_from() -> None:
    # Setup
    row = [Button("Go", "stash:t:i1")]
    rows = [row]
    reply = Reply("hi", rows)  # type: ignore[arg-type]

    # Execute
    row.append(Button("More", "stash:s:i1"))
    rows.append(row)

    # Assert
    assert reply.buttons == ((Button("Go", "stash:t:i1"),),)


def test_the_deferred_notices_cannot_be_changed_at_runtime() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        DEFERRED_TEXT["gpu_busy"] = "changed"  # type: ignore[index]
