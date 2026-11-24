from builders import an_item
from capture_builders import button_labels

from stash.capture import confirmation
from stash.capture.callbacks import FixAction, FixKind
from stash.capture.replies import MARK_DONE_TITLE_LIMIT


def test_a_long_title_is_clipped_in_the_label_and_the_data_stays_within_the_limit() -> None:
    # Setup
    report = an_item(id="r" * 40)
    target = an_item(id="t" * 40, title="Smoke a brisket " * 20)

    # Execute
    reply = confirmation(report, unsure=True, finishes=target)

    # Assert
    button = reply.buttons[1][0]
    assert len(button.label) == len("Mark done: ") + MARK_DONE_TITLE_LIMIT
    assert button.label.endswith("…")
    assert len(button.data.encode()) <= 64
    action = FixAction.parse(button.data)
    assert action == FixAction(FixKind.PROGRESS_DONE, report.id, "t" * 12)


def test_the_reports_own_done_button_is_replaced_by_mark_done() -> None:
    # Execute
    reply = confirmation(an_item(), unsure=True, finishes=an_item(id="t1", title="Fix lamp"))

    # Assert
    assert button_labels(reply.buttons) == [
        ["Type", "Stage"],
        ["Mark done: Fix lamp"],
        ["That was a question →"],
    ]
