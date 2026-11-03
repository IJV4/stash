from datetime import timedelta

from builders import BASE
from capture_builders import a_filing_answer, a_message
from capture_narrowing import handle_deferred, handle_filed
from capture_rig import BURST_WINDOW_SECONDS, build_rig

from stash.capture import Filed, reply_for
from stash.llm import LlmError, LlmUnavailable

WINDOW = timedelta(seconds=BURST_WINDOW_SECONDS)


def test_a_busy_gpu_saves_the_capture_and_a_later_retry_files_it_without_a_second_item() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    rig.busy.busy = True
    result = handle_deferred(rig, a_message("Ramen in Shibuya"))
    pending_while_busy = len(rig.store.pending_captures())
    rig.busy.busy = False

    # Execute
    retried = rig.pipeline.retry_pending()

    # Assert
    assert reply_for(result).text == "📥 Saved — I'll file it when the GPU is free."
    assert pending_while_busy == 1
    assert [type(each) for each in retried] == [Filed]
    assert len(rig.store.list_items()) == 1


def test_an_unreachable_ai_saves_the_capture_and_a_later_retry_files_it() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer(), error=LlmUnavailable("connection refused"))
    result = handle_deferred(rig, a_message("Ramen in Shibuya"))
    pending_while_down = len(rig.store.pending_captures())
    rig.model.error = None

    # Execute
    retried = rig.pipeline.retry_pending()

    # Assert
    assert reply_for(result).text == "📥 Saved — I'll file it once the AI is reachable."
    assert pending_while_down == 1
    assert [type(each) for each in retried] == [Filed]


def test_a_rejected_key_is_treated_like_an_unreachable_ai_and_loses_nothing() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer(), error=LlmError("rejected key"))
    result = handle_deferred(rig, a_message("Ramen in Shibuya"))
    pending_with_bad_key = len(rig.store.pending_captures())
    rig.model.error = None

    # Execute
    rig.pipeline.retry_pending()

    # Assert
    assert reply_for(result).text == "📥 Saved — I'll file it once the AI is reachable."
    assert pending_with_bad_key == 1
    assert len(rig.store.list_items()) == 1


def test_a_forwarded_backlog_gets_one_combined_reply_only_after_the_burst_window() -> None:
    # Setup
    rig = build_rig()
    for message_id, title, item_type in [
        ("m1", "Ichiran ramen", "place"),
        ("m2", "Dune", "book"),
        ("m3", "Sell candles", "idea"),
    ]:
        rig.model.reply = a_filing_answer(title=title, item_type=item_type, details={})
        rig.bursts.add(handle_filed(rig, a_message(title, message_id=message_id)), BASE)

    # Execute
    before_the_window = rig.bursts.due(BASE + WINDOW - timedelta(seconds=1))
    combined = rig.bursts.due(BASE + WINDOW)

    # Assert
    assert before_the_window is None
    assert combined is not None
    assert combined.text == (
        "✅ Saved 3 items:\n• Places · Ichiran ramen\n• Books · Dune\n• Ideas · Sell candles"
    )
