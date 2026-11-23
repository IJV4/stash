from datetime import timedelta

from builders import fetched_item
from capture_builders import (
    FORCED_QUESTION,
    QUESTION,
    RAMEN_URL,
    a_filing_answer,
    a_message,
    a_request_answer,
    an_unsure_answer,
    button_data,
    button_labels,
)
from capture_rig import CaptureRig, build_rig
from clocks import SettableClock
from lifecycle_rig import a_lifecycle
from link_builders import a_link_info

from stash.capture import Filed, IsRequest, Reply, Reroute, gone, reply_for
from stash.capture.fixes import HISTORY_KEPT
from stash.domain import CaptureStatus, Item, ItemType, Stage


def test_a_question_creates_no_item_and_is_marked_as_a_request_for_the_assistant() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())

    # Execute
    result = rig.pipeline.handle(a_message(QUESTION))
    assert isinstance(result, IsRequest)

    # Assert
    stored = rig.store.get_capture(result.capture.id)
    assert stored is not None
    assert (rig.store.list_items(), stored.status, result.capture.text) == (
        [],
        CaptureStatus.REQUEST,
        QUESTION,
    )


def test_a_message_starting_with_a_question_mark_is_handled_as_a_request_without_the_ai() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())

    # Execute
    result = rig.pipeline.handle(a_message(FORCED_QUESTION))

    # Assert
    assert (type(result), rig.model.calls, rig.store.list_items(), rig.inspector.inspected) == (
        IsRequest,
        [],
        [],
        [],
    )


def test_an_unsure_ai_files_the_item_and_the_question_button_reroutes_it_exactly_once() -> None:
    # Setup
    rig = build_rig(answer=an_unsure_answer())
    result = rig.pipeline.handle(a_message(QUESTION))
    assert isinstance(result, Filed)
    reply = reply_for(result)
    data = button_data(reply, "That was a question →")

    # Execute
    first = rig.fixes.apply(data)
    second = rig.fixes.apply(data)

    # Assert
    stored = rig.store.get_capture(result.item.capture_id)
    assert stored is not None
    assert (first, rig.store.list_items(), stored.status, second) == (
        Reroute(QUESTION),
        [],
        CaptureStatus.REQUEST,
        gone(),
    )


def test_the_question_button_of_a_completed_kept_item_with_children_changes_nothing() -> None:
    # Setup
    clock = SettableClock()
    rig = build_rig(answer=an_unsure_answer(), clock=clock)
    result = rig.pipeline.handle(a_message(QUESTION))
    assert isinstance(result, Filed)
    question_button = button_data(reply_for(result), "That was a question →")
    done = pressed(rig, reply_for(result), "Done ✓")
    kept = pressed(rig, pressed(rig, done, "⭐5"), "Keep 📚")
    assert kept.text == f"📚 Kept: {result.item.title}"
    lifecycle = a_lifecycle(rig.store, clock=clock)
    [outcome] = rig.store.outcomes_for(result.item.id)
    lifecycle.annotate(outcome.id, takeaways=["Ask first"])
    for message_id in ("m2", "m3"):
        child = rig.pipeline.handle(a_message("a side note", message_id=message_id))
        assert isinstance(child, Filed)
        lifecycle.group(child.item.id, result.item.id)
    before = group_snapshot(rig, result.item)

    # Execute
    answer = rig.fixes.apply(question_button)

    # Assert
    assert (answer, group_snapshot(rig, result.item)) == (Reply(HISTORY_KEPT), before)


def group_snapshot(rig: CaptureRig, item: Item) -> tuple[object, ...]:
    return (
        rig.store.get_item(item.id),
        rig.store.outcomes_for(item.id),
        rig.store.children_of(item.id),
        rig.store.get_capture(item.capture_id),
    )


def test_choosing_recipes_from_the_type_menu_retypes_the_item_and_shows_the_confirmation() -> None:
    # Setup
    rig = build_rig(
        answer=a_filing_answer(),
        links={RAMEN_URL: a_link_info(url=RAMEN_URL, platform="web")},
    )
    result = rig.pipeline.handle(a_message(RAMEN_URL))
    assert isinstance(result, Filed)
    menu = rig.fixes.apply(button_data(reply_for(result), "Type"))
    assert not isinstance(menu, Reroute)

    # Execute
    reply = rig.fixes.apply(button_data(menu, "Recipes"))
    assert not isinstance(reply, Reroute)

    # Assert
    [item] = rig.store.list_items()
    assert (reply.text, item.item_type) == ("✅ Recipes · Tokyo · Want to", ItemType.RECIPE)


def test_a_stale_or_forged_button_answers_that_the_item_no_longer_exists_and_never_fails() -> None:
    # Setup
    rig = build_rig()
    unknown_item = "stash:t:" + "f" * 32

    # Execute
    answers = [rig.fixes.apply(data) for data in (unknown_item, "garbage", "stash:zz", "")]

    # Assert
    assert answers == [gone()] * 4


FILED_TITLE = "Ichiran ramen"
SIXTY_SECONDS = timedelta(seconds=60)
ONE_SECOND = timedelta(seconds=1)
FOOTER = "Tell me notes or takeaways any time."
RATING_LABELS = ["⭐1", "⭐2", "⭐3", "⭐4", "⭐5"]
KEEP_LABELS = ["Keep 📚", "Not keeping"]


def filed_confirmation(rig: CaptureRig) -> tuple[Item, Reply]:
    result = rig.pipeline.handle(a_message())
    assert isinstance(result, Filed)
    return result.item, reply_for(result)


def pressed(rig: CaptureRig, reply: Reply, label: str) -> Reply:
    answer = rig.fixes.apply(button_data(reply, label))
    assert isinstance(answer, Reply)
    return answer


def test_pressing_done_on_a_filed_item_completes_it_once_and_offers_a_rating_and_keep() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    item, confirmation = filed_confirmation(rig)

    # Execute
    reply = pressed(rig, confirmation, "Done ✓")

    # Assert
    assert (
        fetched_item(rig.store, item.id).stage,
        len(rig.store.outcomes_for(item.id)),
        reply.text,
        button_labels(reply.buttons),
    ) == (
        Stage.DONE,
        1,
        f"🎉 Done: {FILED_TITLE}\n{FOOTER}",
        [RATING_LABELS, KEEP_LABELS],
    )


def test_pressing_a_star_rating_rates_the_outcome_and_keeps_only_the_keep_row() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    item, confirmation = filed_confirmation(rig)
    done = pressed(rig, confirmation, "Done ✓")

    # Execute
    reply = pressed(rig, done, "⭐4")

    # Assert
    [outcome] = rig.store.outcomes_for(item.id)
    assert (outcome.rating, reply.text, button_labels(reply.buttons)) == (
        4,
        f"🎉 Done: {FILED_TITLE} · ⭐4",
        [KEEP_LABELS],
    )


def test_pressing_keep_keeps_the_item_and_answers_that_it_is_kept() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    item, confirmation = filed_confirmation(rig)
    done = pressed(rig, confirmation, "Done ✓")

    # Execute
    reply = pressed(rig, done, "Keep 📚")

    # Assert
    kept = rig.store.get_item(item.id)
    assert (kept and kept.kept, reply.text, button_labels(reply.buttons)) == (
        True,
        f"📚 Kept: {FILED_TITLE}",
        [RATING_LABELS],
    )


def test_pressing_done_a_minute_later_records_a_second_outcome_and_answers_again() -> None:
    # Setup
    clock = SettableClock()
    rig = build_rig(answer=a_filing_answer(), clock=clock)
    item, confirmation = filed_confirmation(rig)
    pressed(rig, confirmation, "Done ✓")
    [first] = rig.store.outcomes_for(item.id)
    clock.advance(SIXTY_SECONDS)

    # Execute
    reply = pressed(rig, confirmation, "Done ✓")

    # Assert
    outcomes = rig.store.outcomes_for(item.id)
    assert first in outcomes
    assert len(outcomes) == 2
    assert reply.text.splitlines()[0] == f"🎉 Done: {FILED_TITLE} (again)"


def test_pressing_done_twice_within_a_minute_records_one_outcome_and_answers_the_same() -> None:
    # Setup
    clock = SettableClock()
    rig = build_rig(answer=a_filing_answer(), clock=clock)
    item, confirmation = filed_confirmation(rig)
    first = pressed(rig, confirmation, "Done ✓")
    clock.advance(SIXTY_SECONDS - ONE_SECOND)

    # Execute
    reply = pressed(rig, confirmation, "Done ✓")

    # Assert
    assert len(rig.store.outcomes_for(item.id)) == 1
    assert reply == first


def test_a_progress_report_judged_a_request_is_filed_unsure_with_the_question_button() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())

    # Execute
    result = rig.pipeline.handle(a_message("finished Tidewater Notes, loved the ending"))

    # Assert
    assert isinstance(result, Filed)
    assert (result.unsure, button_labels(reply_for(result).buttons)[-1]) == (
        True,
        ["That was a question →"],
    )
