import pytest
from builders import MAX_LENGTH_ID, NON_DONE_STAGES, an_item, an_item_at, an_outcome
from capture_builders import button_labels

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT
from stash.capture.completion_replies import done_reply, kept_reply, rated_reply
from stash.capture.menus import stage_menu
from stash.capture.replies import Button, Reply, confirmation, refused
from stash.domain import Stage
from stash.lifecycle.results import Completion

FOOTER = "Tell me notes or takeaways any time."
KEEP_ROW = (Button("Keep 📚", "stash:k:i1:1"), Button("Not keeping", "stash:k:i1:0"))
DONE_ROW = (Button("Done ✓", "stash:d:i1"),)


def a_completion(repeat: bool = False, **item_overrides: object) -> Completion:
    item = an_item(id="i1", stage=Stage.DONE, **item_overrides)
    return Completion(item, an_outcome(id="o1", item_id="i1"), repeat)


def test_a_done_reply_celebrates_the_title_and_invites_notes_in_a_footer() -> None:
    # Execute
    reply = done_reply(a_completion())

    # Assert
    assert reply.text == f"🎉 Done: Ramen in Shibuya\n{FOOTER}"


def test_a_done_reply_for_a_repeat_marks_the_title_again() -> None:
    # Execute
    reply = done_reply(a_completion(repeat=True))

    # Assert
    assert reply.text == f"🎉 Done: Ramen in Shibuya (again)\n{FOOTER}"


def test_a_done_reply_offers_a_rating_row_then_the_keep_row() -> None:
    # Execute
    reply = done_reply(a_completion())

    # Assert
    assert button_labels(reply.buttons) == [
        ["⭐1", "⭐2", "⭐3", "⭐4", "⭐5"],
        ["Keep 📚", "Not keeping"],
    ]


def test_the_rating_row_of_a_done_reply_runs_from_one_star_to_five() -> None:
    # Execute
    reply = done_reply(a_completion())

    # Assert
    assert button_labels(reply.buttons)[0] == ["⭐1", "⭐2", "⭐3", "⭐4", "⭐5"]


def test_each_rating_button_carries_the_outcome_id_and_its_rating() -> None:
    # Execute
    reply = done_reply(a_completion())

    # Assert
    assert [button.data for button in reply.buttons[0]] == [
        "stash:r:o1:1",
        "stash:r:o1:2",
        "stash:r:o1:3",
        "stash:r:o1:4",
        "stash:r:o1:5",
    ]


def test_the_keep_row_of_a_done_reply_offers_keep_and_not_keeping_for_the_item() -> None:
    # Execute
    reply = done_reply(a_completion())

    # Assert
    assert reply.buttons[1] == KEEP_ROW


def test_a_done_reply_for_a_repeat_offers_the_same_buttons_for_the_new_outcome() -> None:
    # Execute
    reply = done_reply(a_completion(repeat=True))

    # Assert
    assert reply.buttons == done_reply(a_completion()).buttons


def test_a_rated_reply_names_the_title_and_the_rating() -> None:
    # Execute
    reply = rated_reply(a_completion().item, 4)

    # Assert
    assert reply.text == "🎉 Done: Ramen in Shibuya · ⭐4"


def test_a_rated_reply_keeps_only_the_keep_row() -> None:
    # Execute
    reply = rated_reply(a_completion().item, 4)

    # Assert
    assert reply.buttons == (KEEP_ROW,)


def test_a_kept_item_is_celebrated_with_its_title_and_no_buttons() -> None:
    # Execute
    reply = kept_reply(a_completion(kept=True).item)

    # Assert
    assert reply == Reply("📚 Kept: Ramen in Shibuya", ())


def test_an_item_the_owner_is_not_keeping_gets_a_plain_acknowledgement_and_no_buttons() -> None:
    # Execute
    reply = kept_reply(a_completion(kept=False).item)

    # Assert
    assert reply == Reply("Okay, not keeping Ramen in Shibuya.", ())


def test_a_refusal_quotes_the_reason_and_has_no_buttons() -> None:
    # Execute
    reply = refused("only done items can be kept")

    # Assert
    assert reply == Reply("I can't do that: only done items can be kept", ())


def test_every_completion_button_for_maximum_length_ids_fits_the_telegram_limit() -> None:
    # Setup
    item = an_item(id=MAX_LENGTH_ID, stage=Stage.DONE)
    outcome = an_outcome(id=MAX_LENGTH_ID, item_id=MAX_LENGTH_ID)
    replies = [done_reply(Completion(item, outcome, repeat=True)), rated_reply(item, 5)]

    # Execute
    longest = max(
        len(button.data.encode("utf-8"))
        for reply in replies
        for row in reply.buttons
        for button in row
    )

    # Assert
    assert longest <= TELEGRAM_CALLBACK_LIMIT


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_a_confirmation_of_an_item_that_is_not_done_offers_a_done_button_after_type_and_stage(
    stage: Stage,
) -> None:
    # Execute
    reply = confirmation(an_item_at(stage), unsure=False)

    # Assert
    assert reply.buttons[1] == DONE_ROW


def test_an_unsure_confirmation_puts_the_done_row_before_the_question_row() -> None:
    # Execute
    reply = confirmation(an_item_at(Stage.INBOX), unsure=True)

    # Assert
    assert button_labels(reply.buttons) == [
        ["Type", "Stage"],
        ["Done ✓"],
        ["That was a question →"],
    ]


def test_a_confirmation_of_a_done_item_has_no_done_button() -> None:
    # Execute
    reply = confirmation(an_item_at(Stage.DONE), unsure=False)

    # Assert
    assert button_labels(reply.buttons) == [["Type", "Stage"]]


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_the_stage_menu_of_an_item_that_is_not_done_ends_with_the_done_button(
    stage: Stage,
) -> None:
    # Execute
    reply = stage_menu(an_item_at(stage))

    # Assert
    assert reply.buttons[-1] == DONE_ROW


def test_the_stage_menu_of_a_done_item_has_no_done_button() -> None:
    # Execute
    reply = stage_menu(an_item_at(Stage.DONE))

    # Assert
    assert "Done ✓" not in [button.label for row in reply.buttons for button in row]
