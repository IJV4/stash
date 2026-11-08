import asyncio

from app_builders import an_app
from fakes.fake_telegram_bot import FakeTelegramApplication
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_deliveries import ScriptedNudges
from fakes.scripted_sender import ScriptedSender
from fakes.store_factories import FreshStore
from hermes_registration_rig import register_stash
from hermes_rig import until
from nudge_builders import stored_date_night_with_its_step
from planning_builders import stored_date_night
from ticker_rig import OWNER_CHAT, a_ticker, a_ticker_over, proposals_over

TICKS = 3
TICKS_TO_RETRY = 2


def test_connecting_telegram_again_starts_no_second_ticker_until_the_first_has_ended() -> None:
    # Setup
    nudges = ScriptedNudges()
    plugin = register_stash(an_app(nudge_delivery=nudges))

    async def scenario() -> tuple[int, int]:
        plugin.ctx.connect("telegram", plugin.application)
        plugin.ctx.connect("telegram", FakeTelegramApplication())
        started_while_running = len(plugin.ctx.spawned)
        await until(lambda: nudges.nows)
        await plugin.ctx.cancel_spawned()
        plugin.ctx.connect("telegram", FakeTelegramApplication())
        started_after_it_ended = len(plugin.ctx.spawned)
        await plugin.ctx.cancel_spawned()
        return started_while_running, started_after_it_ended

    # Execute
    started = asyncio.run(scenario())

    # Assert
    assert started == (1, 2)


def test_a_reminder_whose_send_failed_is_sent_to_the_owner_chat_once_on_the_next_tick() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    sender = ScriptedSender(failures=1)
    ticker = a_ticker_over(store, sender)

    async def scenario() -> None:
        for _ in range(TICKS):
            await ticker.tick()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (sender.attempts, [chat for chat, _ in sender.sent]) == (2, [OWNER_CHAT])


def test_an_item_whose_proposal_send_failed_is_proposed_and_sent_by_the_next_tick() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    sender = ScriptedSender(failures=1)
    ticker = a_ticker(ScriptedNudges(), proposals_over(store), sender, PausingScheduler())

    async def scenario() -> None:
        for _ in range(TICKS_TO_RETRY):
            await ticker.tick()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (sender.attempts, len(sender.sent)) == (2, 1)
