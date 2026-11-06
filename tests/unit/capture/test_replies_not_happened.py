import pytest
from builders import an_item_at

from stash.capture.completion_replies import didnt_happen_reply
from stash.capture.replies import Reply
from stash.domain import Stage

STAGES_OTHER_THAN_WANT_TO = [stage for stage in Stage if stage is not Stage.WANT_TO]


def test_an_item_in_want_to_is_announced_as_being_in_want_to() -> None:
    # Setup
    item = an_item_at(Stage.WANT_TO, title="Date night")

    # Execute
    reply = didnt_happen_reply(item)

    # Assert
    assert reply == Reply("↩️ Okay, Date night is in Want to.")


@pytest.mark.parametrize("stage", STAGES_OTHER_THAN_WANT_TO)
def test_an_item_in_another_stage_is_left_as_it_is_and_says_which_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage, title="Date night")

    # Execute
    reply = didnt_happen_reply(item)

    # Assert
    assert reply == Reply(f"Date night is {stage.label}, so I left it.")
