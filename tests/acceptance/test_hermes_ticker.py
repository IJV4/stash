import asyncio

from app_builders import an_app
from fakes.fake_telegram_bot import FakeTelegramApplication
from fakes.memory_store import MemoryStore
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_deliveries import ScriptedNudges
from fakes.scripted_sender import ScriptedSender
from hermes_registration_rig import register_stash
from hermes_rig import until
from nudge_builders import stored_date_night_with_its_step
from planning_builders import DATE_NIGHT_ID, stored_date_night
from ticker_rig import OWNER_CHAT, a_ticker, a_ticker_over, proposals_over

TICKS = 3


def test_connecting_telegram_twice_starts_one_ticker() -> None:
    # Setup
    plugin = register_stash(an_app(nudge_delivery=ScriptedNudges()))

    async def scenario() -> int:
        plugin.ctx.connect("telegram", plugin.application)
        plugin.ctx.connect("telegram", FakeTelegramApplication())
        started = len(plugin.ctx.spawned)
        await plugin.ctx.cancel_spawned()
        return started

    # Execute
    started = asyncio.run(scenario())

    # Assert
    assert started == 1


def test_a_ticker_that_ended_is_started_again_by_the_next_connection() -> None:
    # Setup
    nudges = ScriptedNudges()
    plugin = register_stash(an_app(nudge_delivery=nudges))

    async def scenario() -> int:
        plugin.ctx.connect("telegram", plugin.application)
        await until(lambda: nudges.nows)
        await plugin.ctx.cancel_spawned()
        plugin.ctx.connect("telegram", FakeTelegramApplication())
        started = len(plugin.ctx.spawned)
        await plugin.ctx.cancel_spawned()
        return started

    # Execute
    started = asyncio.run(scenario())

    # Assert
    assert started == 2


def test_a_due_reminder_is_sent_to_the_owner_chat_once_across_ticks() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night_with_its_step(store)
    sender = ScriptedSender()
    ticker = a_ticker_over(store, sender)

    async def scenario() -> None:
        for _ in range(TICKS):
            await ticker.tick()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [chat for chat, _ in sender.sent] == [OWNER_CHAT]


def test_a_reminder_whose_send_failed_is_sent_on_the_next_tick() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night_with_its_step(store)
    sender = ScriptedSender(failures=1)
    ticker = a_ticker_over(store, sender)

    async def scenario() -> None:
        for _ in range(TICKS):
            await ticker.tick()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (sender.attempts, len(sender.sent)) == (2, 1)


def test_a_proposal_whose_send_failed_is_discarded() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night(store)
    ticker = a_ticker(
        ScriptedNudges(), proposals_over(store), ScriptedSender(failures=1), PausingScheduler()
    )

    # Execute
    asyncio.run(ticker.tick())

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == []
