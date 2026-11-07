import asyncio
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_deliveries import ScriptedNudges, ScriptedProposals
from fakes.scripted_sender import ScriptedSender
from hermes_rig import until
from log_records import recording_logs
from threads import OVERLAP_GRACE_SECONDS
from ticker_rig import (
    a_ticker,
    nudges_blocked_until_released,
)

from stash.capture import Reply
from stash.hermes_adapter.ticker import (
    NUDGE_DELIVERY_FAILED_LOG,
    PROPOSAL_DELIVERY_FAILED_LOG,
    TICKER_STOPPED_LOG,
    TickerLauncher,
)

TICKER_LOGGER = "stash.hermes_adapter.ticker"
SHORT_SEND_TIMEOUT_S = 0.005
TICK_LIMIT_S = 2.0
TICKS_OBSERVED = 2


def store_is_locked() -> None:
    raise RuntimeError("store is locked")


def test_a_delivery_that_fails_is_logged_and_does_not_stop_the_next_delivery_or_the_tick() -> None:
    # Setup
    ticker = a_ticker(ScriptedNudges(store_is_locked), ScriptedProposals(store_is_locked))

    # Execute
    with recording_logs(TICKER_LOGGER) as logs:
        asyncio.run(ticker.tick())

    # Assert
    assert logs.entries() == [
        (logging.ERROR, NUDGE_DELIVERY_FAILED_LOG),
        (logging.ERROR, PROPOSAL_DELIVERY_FAILED_LOG),
    ]


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


def test_a_send_that_never_finishes_is_abandoned_so_the_tick_returns() -> None:
    # Setup
    sender = ScriptedSender(hang=True)
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


class WaitingScheduler(PausingScheduler):
    def __init__(self) -> None:
        super().__init__()
        self.waiting = False

    async def pause(self, seconds: float) -> None:
        self.waiting = True
        await asyncio.Event().wait()


class FailingScheduler(PausingScheduler):
    async def pause(self, seconds: float) -> None:
        raise RuntimeError("scheduler broke")


async def stopped_ticker_logs(
    scheduler: PausingScheduler, cancelled_once: Callable[[], object] | None = None
) -> list[tuple[int, str]]:
    tasks: list[asyncio.Task[None]] = []
    launcher = TickerLauncher()
    with recording_logs(TICKER_LOGGER) as logs:
        launcher.start_once(
            lambda coro: tasks.append(asyncio.create_task(coro)),
            lambda: a_ticker(scheduler=scheduler),
        )
        if cancelled_once is not None:
            await until(cancelled_once)
            tasks[0].cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return logs.entries()


def test_a_cancelled_ticker_logs_a_warning_that_it_stopped() -> None:
    # Setup
    scheduler = WaitingScheduler()

    # Execute
    entries = asyncio.run(stopped_ticker_logs(scheduler, lambda: scheduler.waiting))

    # Assert
    assert entries == [(logging.WARNING, TICKER_STOPPED_LOG)]


def test_a_ticker_that_fails_logs_a_warning_that_it_stopped() -> None:
    # Execute
    entries = asyncio.run(stopped_ticker_logs(FailingScheduler()))

    # Assert
    assert entries == [(logging.WARNING, TICKER_STOPPED_LOG)]
