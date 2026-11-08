import pytest
from builders import (
    NON_DONE_STAGES,
    an_item_at,
)
from capture_builders import button_labels

from stash.capture.menus import stage_menu
from stash.capture.replies import Button, Reply, confirmation, refused
from stash.domain import Stage

FOOTER = "Tell me notes or takeaways any time."
DONE_ROW = (Button("Done ✓", "stash:d:i1"),)


def test_a_refusal_quotes_the_reason_and_has_no_buttons() -> None:
    # Execute
    reply = refused("only done items can be kept")

    # Assert
    assert reply == Reply("I can't do that: only done items can be kept", ())


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
