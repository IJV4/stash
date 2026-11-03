import asyncio
import logging
from datetime import datetime, timedelta

from builders import BASE, a_capture, an_item
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_sender import ScriptedSender
from log_records import recording_logs

from stash.capture import BurstCoalescer, Deferred, Filed, reply_for, summary
from stash.hermes_adapter.bursts import RECHECK_SECONDS, Bursts, ChatBurst

LOGGER = "stash.hermes_adapter.bursts"
CHAT_ID = "1001"
OTHER_CHAT_ID = "1002"
WINDOW_SECONDS = 5.0


def a_filed(item_id: str = "i1") -> Filed:
    return Filed(an_item(id=item_id, title=f"Title {item_id}"), unsure=False)


def a_deferred(capture_id: str = "c1") -> Deferred:
    return Deferred(a_capture(id=capture_id), "gpu_busy")


def a_burst(
    sender: ScriptedSender, scheduler: PausingScheduler, window: float = WINDOW_SECONDS
) -> ChatBurst:
    return ChatBurst(BurstCoalescer(window), CHAT_ID, sender, scheduler)


def test_nothing_is_sent_by_the_time_add_returns() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)

    # Execute
    burst.add(a_filed())
    sent_on_return = list(sender.sent)
    asyncio.run(scheduler.drain())

    # Assert
    assert sent_on_return == []


def test_the_reply_goes_out_only_once_the_window_has_elapsed() -> None:
    # Setup
    scheduler = PausingScheduler()
    sent_at: list[datetime] = []
    sender = ScriptedSender(on_send=lambda: sent_at.append(scheduler.now()))
    burst = a_burst(sender, scheduler)

    # Execute
    burst.add(a_filed())
    asyncio.run(scheduler.drain())

    # Assert
    assert sent_at == [BASE + timedelta(seconds=WINDOW_SECONDS)]


def test_the_pause_before_the_reply_is_the_coalescer_window() -> None:
    # Setup
    scheduler = PausingScheduler()
    burst = a_burst(ScriptedSender(), scheduler, window=2.5)

    # Execute
    burst.add(a_filed())
    asyncio.run(scheduler.drain())

    # Assert
    assert scheduler.requested == [2.5]


def test_a_single_result_is_sent_as_its_own_reply_to_the_chat() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)
    filed = a_filed()

    # Execute
    burst.add(filed)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, reply_for(filed))]


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


def test_adding_while_a_flush_is_waiting_leaves_no_second_flush_polling_for_a_batch() -> None:
    # Setup
    sender = ScriptedSender()
    burst_holder: list[ChatBurst] = []
    scheduler = PausingScheduler(on_pause=lambda: burst_holder[0].add(a_filed("i2")))
    burst = a_burst(sender, scheduler)
    burst_holder.append(burst)

    # Execute
    burst.add(a_filed("i1"))
    asyncio.run(scheduler.drain())

    # Assert
    assert scheduler.failures == []


def test_a_result_added_while_a_flush_is_waiting_joins_that_flush() -> None:
    # Setup
    sender = ScriptedSender()
    burst_holder: list[ChatBurst] = []
    scheduler = PausingScheduler(on_pause=lambda: burst_holder[0].add(a_filed("i2")))
    burst = a_burst(sender, scheduler)
    burst_holder.append(burst)
    first, second = a_filed("i1"), a_filed("i2")

    # Execute
    burst.add(first)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, summary([first, second]))]


def test_a_result_added_while_the_reply_is_being_sent_is_delivered_by_a_new_flush() -> None:
    # Setup
    burst_holder: list[ChatBurst] = []
    second = a_filed("i2")
    sender = ScriptedSender(on_send=lambda: burst_holder[0].add(second))
    scheduler = PausingScheduler()
    burst = a_burst(sender, scheduler)
    burst_holder.append(burst)
    first = a_filed("i1")

    # Execute
    burst.add(first)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, reply_for(first)), (CHAT_ID, reply_for(second))]


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


def test_results_of_two_chats_are_sent_as_separate_replies_to_their_own_chat() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    bursts = Bursts(lambda: BurstCoalescer(WINDOW_SECONDS), sender, scheduler)
    mine, theirs = a_filed("i1"), a_filed("i2")

    # Execute
    bursts.add(CHAT_ID, mine)
    bursts.add(OTHER_CHAT_ID, theirs)
    asyncio.run(scheduler.drain())

    # Assert
    assert dict(sender.sent) == {CHAT_ID: reply_for(mine), OTHER_CHAT_ID: reply_for(theirs)}


def test_results_of_one_chat_are_coalesced_into_one_reply() -> None:
    # Setup
    sender = ScriptedSender()
    scheduler = PausingScheduler()
    bursts = Bursts(lambda: BurstCoalescer(WINDOW_SECONDS), sender, scheduler)
    results = [a_filed("i1"), a_filed("i2")]

    # Execute
    for result in results:
        bursts.add(CHAT_ID, result)
    asyncio.run(scheduler.drain())

    # Assert
    assert sender.sent == [(CHAT_ID, summary(results))]


def test_the_coalescer_factory_is_called_once_per_chat() -> None:
    # Setup
    created: list[BurstCoalescer] = []

    def factory() -> BurstCoalescer:
        created.append(BurstCoalescer(WINDOW_SECONDS))
        return created[-1]

    scheduler = PausingScheduler()
    bursts = Bursts(factory, ScriptedSender(), scheduler)

    # Execute
    bursts.add(CHAT_ID, a_filed("i1"))
    bursts.add(CHAT_ID, a_filed("i2"))
    bursts.add(OTHER_CHAT_ID, a_filed("i3"))
    asyncio.run(scheduler.drain())

    # Assert
    assert len(created) == 2
