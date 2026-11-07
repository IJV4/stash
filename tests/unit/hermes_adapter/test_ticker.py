import asyncio
import logging
import threading
from collections.abc import Coroutine
from typing import Any

import pytest
from fakes.hanging_sender import HangingSender
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_deliveries import ScriptedNudges, ScriptedProposals
from log_records import recording_logs
from nudge_builders import SATURDAY_MORNING
from threads import OVERLAP_GRACE_SECONDS
from ticker_rig import (
    INTERVAL_S,
    a_ticker,
    nudges_blocked_until_released,
    run_until,
)

from stash.capture import Reply
from stash.hermes_adapter.ticker import (
    NUDGE_DELIVERY_FAILED_LOG,
    PROPOSAL_DELIVERY_FAILED_LOG,
    TickerLauncher,
)

TICKER_LOGGER = "stash.hermes_adapter.ticker"
SHORT_SEND_TIMEOUT_S = 0.005
TICK_LIMIT_S = 2.0
TICKS_OBSERVED = 2


def store_is_locked() -> None:
    raise RuntimeError("store is locked")


def test_a_delivery_that_fails_is_logged_and_the_tick_still_returns() -> None:
    # Setup
    ticker = a_ticker(ScriptedNudges(store_is_locked))

    # Execute
    with recording_logs(TICKER_LOGGER) as logs:
        asyncio.run(ticker.tick())

    # Assert
    assert logs.entries() == [(logging.ERROR, NUDGE_DELIVERY_FAILED_LOG)]


def test_a_failing_nudge_delivery_does_not_skip_the_proposals() -> None:
    # Setup
    proposals = ScriptedProposals()
    ticker = a_ticker(ScriptedNudges(store_is_locked), proposals)

    # Execute
    asyncio.run(ticker.tick())

    # Assert
    assert len(proposals.threads) == 1


def test_a_failing_proposal_delivery_is_logged_and_the_tick_still_returns() -> None:
    # Setup
    ticker = a_ticker(proposals=ScriptedProposals(store_is_locked))

    # Execute
    with recording_logs(TICKER_LOGGER) as logs:
        asyncio.run(ticker.tick())

    # Assert
    assert logs.entries() == [(logging.ERROR, PROPOSAL_DELIVERY_FAILED_LOG)]


def test_the_deliveries_run_off_the_event_loop_thread() -> None:
    # Setup
    nudges, proposals = ScriptedNudges(), ScriptedProposals()

    async def scenario() -> int:
        await a_ticker(nudges, proposals).tick()
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert loop_thread not in nudges.threads + proposals.threads


def test_the_deliveries_are_told_the_time_of_the_scheduler() -> None:
    # Setup
    nudges = ScriptedNudges()
    ticker = a_ticker(nudges, scheduler=PausingScheduler(start=SATURDAY_MORNING))

    # Execute
    asyncio.run(ticker.tick())

    # Assert
    assert nudges.nows == [SATURDAY_MORNING]


def test_two_ticks_started_together_never_overlap() -> None:
    # Setup
    blocked = nudges_blocked_until_released()
    ticker = a_ticker(blocked.nudges)

    async def scenario() -> None:
        ticks = asyncio.gather(ticker.tick(), ticker.tick())
        await blocked.until_inside()
        await asyncio.sleep(OVERLAP_GRACE_SECONDS)
        blocked.gate.release.set()
        await asyncio.wait_for(ticks, TICK_LIMIT_S)

    # Execute
    asyncio.run(scenario())

    # Assert
    assert blocked.gate.max_inside == 1


def test_cancelling_the_ticker_mid_tick_leaves_the_next_tick_free_to_run() -> None:
    # Setup
    blocked = nudges_blocked_until_released()
    ticker = a_ticker(blocked.nudges)

    async def scenario() -> None:
        task = asyncio.create_task(ticker.run_forever())
        await blocked.until_inside()
        task.cancel()
        blocked.gate.release.set()
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.wait_for(ticker.tick(), TICK_LIMIT_S)

    # Execute
    asyncio.run(scenario())

    # Assert
    assert len(blocked.nudges.nows) == TICKS_OBSERVED


def test_the_ticker_pauses_the_interval_between_ticks() -> None:
    # Setup
    scheduler = PausingScheduler()
    ticker = a_ticker(scheduler=scheduler)

    # Execute
    asyncio.run(run_until(ticker, lambda: len(scheduler.requested) >= TICKS_OBSERVED))

    # Assert
    assert scheduler.requested[:TICKS_OBSERVED] == [INTERVAL_S] * TICKS_OBSERVED


def test_the_ticker_keeps_ticking_after_a_delivery_fails() -> None:
    # Setup
    nudges = ScriptedNudges(store_is_locked)
    ticker = a_ticker(nudges)

    # Execute
    asyncio.run(run_until(ticker, lambda: len(nudges.nows) >= TICKS_OBSERVED))

    # Assert
    assert len(nudges.nows) >= TICKS_OBSERVED


def test_a_send_that_never_finishes_is_abandoned_so_the_tick_returns() -> None:
    # Setup
    sender = HangingSender()
    nudges = ScriptedNudges(replies=(Reply("Book the table"),))
    ticker = a_ticker(nudges, sender=sender, send_timeout_s=SHORT_SEND_TIMEOUT_S)

    async def scenario() -> int:
        await asyncio.wait_for(ticker.tick(), TICK_LIMIT_S)
        await asyncio.sleep(0)
        return sender.cancelled

    # Execute
    cancelled_before_the_loop_closed = asyncio.run(scenario())

    # Assert
    assert cancelled_before_the_loop_closed == 1


def test_a_launcher_whose_spawn_refused_can_start_a_ticker_again() -> None:
    # Setup
    launcher = TickerLauncher()
    started: list[str] = []

    def refusing(coro: Coroutine[Any, Any, None]) -> object:
        coro.close()
        raise RuntimeError("no running loop")

    def accepting(coro: Coroutine[Any, Any, None]) -> object:
        started.append("started")
        coro.close()
        return None

    with pytest.raises(RuntimeError):
        launcher.start_once(refusing, a_ticker)

    # Execute
    launcher.start_once(accepting, a_ticker)

    # Assert
    assert started == ["started"]
