import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

from builders import BASE
from log_records import recording_logs

from stash.hermes_adapter.scheduler import LoopScheduler

T = TypeVar("T")
LOGGER = "stash.hermes_adapter.scheduler"
TEST_DEADLINE_SECONDS = 2.0


def run_bounded(scenario: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(asyncio.wait_for(scenario, TEST_DEADLINE_SECONDS))


class RecordingSleep:
    def __init__(self) -> None:
        self.requested: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.requested.append(seconds)


def a_scheduler(sleep: RecordingSleep | None = None) -> LoopScheduler:
    recorder = RecordingSleep() if sleep is None else sleep
    return LoopScheduler(lambda: BASE, recorder.sleep)


def test_now_reads_the_injected_clock() -> None:
    # Setup
    scheduler = LoopScheduler(lambda: BASE)

    # Execute
    now = scheduler.now()

    # Assert
    assert now == BASE


def test_pause_delegates_to_the_injected_sleep() -> None:
    # Setup
    sleep = RecordingSleep()
    scheduler = a_scheduler(sleep=sleep)

    # Execute
    asyncio.run(scheduler.pause(2.5))

    # Assert
    assert sleep.requested == [2.5]


def test_pause_without_an_injected_sleep_waits_on_the_event_loop() -> None:
    # Setup
    scheduler = LoopScheduler(lambda: BASE)

    # Execute
    outcome = asyncio.run(scheduler.pause(0))

    # Assert
    assert outcome is None


def test_a_spawned_coroutine_runs_to_completion_by_the_time_drain_returns() -> None:
    # Setup
    scheduler = a_scheduler()
    ran: list[str] = []

    async def job() -> None:
        await asyncio.sleep(0)
        ran.append("job")

    async def scenario() -> None:
        scheduler.spawn(job(), "job")
        await scheduler.drain()

    # Execute
    run_bounded(scenario())

    # Assert
    assert ran == ["job"]


def test_drain_also_waits_for_tasks_spawned_by_tasks() -> None:
    # Setup
    scheduler = a_scheduler()
    ran: list[str] = []

    async def grandchild() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        ran.append("grandchild")

    async def child() -> None:
        scheduler.spawn(grandchild(), "grandchild")
        ran.append("child")

    async def scenario() -> None:
        scheduler.spawn(child(), "child")
        await scheduler.drain()

    # Execute
    run_bounded(scenario())

    # Assert
    assert ran == ["child", "grandchild"]


def test_drain_returns_at_once_when_nothing_was_spawned() -> None:
    # Setup
    scheduler = a_scheduler()

    # Execute
    outcome = run_bounded(scheduler.drain())

    # Assert
    assert outcome is None


def test_a_failing_task_does_not_stop_drain_from_returning() -> None:
    # Setup
    scheduler = a_scheduler()

    async def boom() -> None:
        raise RuntimeError("boom")

    async def scenario() -> str:
        scheduler.spawn(boom(), "boom")
        await scheduler.drain()
        return "drained"

    # Execute
    outcome = run_bounded(scenario())

    # Assert
    assert outcome == "drained"


def test_a_failing_task_is_logged_as_an_error_naming_the_task() -> None:
    # Setup
    scheduler = a_scheduler()

    async def boom() -> None:
        raise RuntimeError("boom")

    async def scenario() -> None:
        scheduler.spawn(boom(), "process-c-7")
        await scheduler.drain()

    # Execute
    with recording_logs(LOGGER) as logs:
        run_bounded(scenario())

    # Assert
    assert logs.entries() == [(logging.ERROR, "task process-c-7 failed")]


def test_a_task_that_succeeds_logs_nothing() -> None:
    # Setup
    scheduler = a_scheduler()

    async def fine() -> None:
        return None

    async def scenario() -> None:
        scheduler.spawn(fine(), "fine")
        await scheduler.drain()

    # Execute
    with recording_logs(LOGGER) as logs:
        run_bounded(scenario())

    # Assert
    assert logs.entries() == []


def test_a_failing_task_does_not_stop_the_other_tasks() -> None:
    # Setup
    scheduler = a_scheduler()
    ran: list[str] = []

    async def boom() -> None:
        raise RuntimeError("boom")

    async def fine() -> None:
        ran.append("fine")

    async def scenario() -> None:
        scheduler.spawn(boom(), "boom")
        scheduler.spawn(fine(), "fine")
        await scheduler.drain()

    # Execute
    run_bounded(scenario())

    # Assert
    assert ran == ["fine"]


def test_a_cancelled_task_is_not_logged_as_a_failure() -> None:
    # Setup
    scheduler = a_scheduler()

    async def forever() -> None:
        await asyncio.Event().wait()

    async def scenario() -> None:
        scheduler.spawn(forever(), "forever")
        await asyncio.sleep(0)
        for task in asyncio.all_tasks():
            if task.get_name() == "forever":
                task.cancel()
        await scheduler.drain()

    # Execute
    with recording_logs(LOGGER) as logs:
        run_bounded(scenario())

    # Assert
    assert logs.entries() == []
