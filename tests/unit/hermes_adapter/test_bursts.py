import asyncio
import logging

from builders import a_capture, an_item
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_sender import ScriptedSender
from log_records import recording_logs

from stash.capture import BurstCoalescer, Deferred, Filed, reply_for, summary
from stash.hermes_adapter.bursts import RECHECK_SECONDS, ChatBurst

LOGGER = "stash.hermes_adapter.bursts"
CHAT_ID = "1001"
WINDOW_SECONDS = 5.0


def a_filed(item_id: str = "i1") -> Filed:
    return Filed(an_item(id=item_id, title=f"Title {item_id}"), unsure=False)


def a_deferred(capture_id: str = "c1") -> Deferred:
    return Deferred(a_capture(id=capture_id), "gpu_busy")


def a_burst(
    sender: ScriptedSender, scheduler: PausingScheduler, window: float = WINDOW_SECONDS
) -> ChatBurst:
    return ChatBurst(BurstCoalescer(window), CHAT_ID, sender, scheduler)


def test_several_results_inside_the_window_are_sent_as_one_summary() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)
    results: list[Filed | Deferred] = [a_filed("i1"), a_deferred("c2"), a_filed("i3")]

    # Execute
    for result in results:
        burst.add(result)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, summary(results))]


def test_an_item_added_twice_in_a_window_is_listed_once() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)
    filed = a_filed()

    # Execute
    burst.add(filed)
    burst.add(filed)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, reply_for(filed))]


def test_the_flush_pauses_again_when_the_clock_has_not_yet_passed_the_window() -> None:
    # Setup
    scheduler = PausingScheduler(advances=[4.0, 1.0])
    burst = a_burst(ScriptedSender(), scheduler)

    # Execute
    burst.add(a_filed())
    asyncio.run(scheduler.drain())

    # Assert
    assert scheduler.requested == [WINDOW_SECONDS, RECHECK_SECONDS]


def test_the_reply_is_sent_once_the_recheck_finds_the_window_elapsed() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler(advances=[4.0, 1.0])
    burst = a_burst(sender, scheduler)
    filed = a_filed()

    # Execute
    burst.add(filed)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, reply_for(filed))]


def test_a_send_failure_is_swallowed() -> None:
    # Setup
    scheduler = PausingScheduler()
    burst = a_burst(ScriptedSender(failures=1), scheduler)

    # Execute
    burst.add(a_filed())
    asyncio.run(scheduler.drain())

    # Assert
    assert scheduler.failures == []


def test_a_send_failure_is_logged_as_an_error_naming_the_chat_but_not_the_text() -> None:
    # Setup
    scheduler = PausingScheduler()
    burst = a_burst(ScriptedSender(failures=1), scheduler)
    filed = a_filed()

    # Execute
    with recording_logs(LOGGER) as logs:
        burst.add(filed)
        asyncio.run(scheduler.drain())

    # Assert
    assert logs.entries() == [(logging.ERROR, f"could not send the burst reply to chat {CHAT_ID}")]


def test_the_next_result_after_a_send_failure_starts_a_new_flush() -> None:
    # Setup
    sender = ScriptedSender(failures=1)
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)
    second = a_filed("i2")
    burst.add(a_filed("i1"))
    asyncio.run(scheduler.drain())

    # Execute
    burst.add(second)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, reply_for(second))]
