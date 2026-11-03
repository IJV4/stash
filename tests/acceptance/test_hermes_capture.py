import asyncio

from capture_builders import a_filing_answer
from fakes.raising_intake import RaisingIntake
from hermes_events import OWNER_ID, STRANGER_ID, an_event
from hermes_rig import build_hermes_rig

from stash.hermes_adapter.events import Chat
from stash.llm import LlmUnavailable

QUESTION = "what can I do Saturday afternoon?"
SKIP = {"action": "skip"}
ALLOW = {"action": "allow"}


class SaveFailed(Exception):
    pass


class FilingExploded(Exception):
    pass


def test_a_plain_message_from_the_owner_is_skipped_and_confirmed_after_the_burst_window() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    async def scenario() -> dict[str, str]:
        verdict = await rig.intake.on_dispatch(an_event())
        await rig.scheduler.drain()
        return verdict

    # Execute
    verdict = asyncio.run(scenario())

    # Assert
    assert (verdict, rig.outbox.sent_texts()) == (SKIP, ["✅ Places · Tokyo · Want to"])


def test_a_message_starting_with_a_slash_is_allowed_through_and_stores_nothing() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    async def scenario() -> dict[str, str]:
        verdict = await rig.intake.on_dispatch(an_event(text="/list"))
        await rig.scheduler.drain()
        return verdict

    # Execute
    verdict = asyncio.run(scenario())

    # Assert
    assert (verdict, rig.capture.store.pending_captures(), rig.capture.store.list_items()) == (
        ALLOW,
        [],
        [],
    )


def test_a_message_from_anybody_else_is_allowed_through_stores_nothing_and_sends_nothing() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    async def scenario() -> dict[str, str]:
        verdict = await rig.intake.on_dispatch(an_event(user_id=STRANGER_ID))
        await rig.scheduler.drain()
        return verdict

    # Execute
    verdict = asyncio.run(scenario())

    # Assert
    assert (verdict, rig.capture.store.list_items(), rig.outbox.sent) == (ALLOW, [], [])


def test_the_same_telegram_message_delivered_twice_is_one_item_and_one_reply() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    async def scenario() -> list[dict[str, str]]:
        verdicts = [await rig.intake.on_dispatch(an_event()) for _ in range(2)]
        await rig.scheduler.drain()
        return verdicts

    # Execute
    verdicts = asyncio.run(scenario())

    # Assert
    assert (verdicts, len(rig.capture.store.list_items()), len(rig.outbox.sent)) == (
        [SKIP, SKIP],
        1,
        1,
    )


def test_several_messages_inside_the_burst_window_get_one_combined_reply() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())
    messages = [("m1", "Ramen in Shibuya"), ("m2", "Pasta in Rome"), ("m3", "Tacos in Mexico City")]

    async def scenario() -> None:
        for message_id, text in messages:
            await rig.intake.on_dispatch(an_event(text=text, message_id=message_id))
        await rig.scheduler.drain()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [text.splitlines()[0] for text in rig.outbox.sent_texts()] == ["✅ Saved 3 items:"]


def test_when_the_ai_is_down_the_owner_is_told_it_is_saved_and_the_capture_stays_pending() -> None:
    # Setup
    rig = build_hermes_rig(error=LlmUnavailable("connection refused"))

    async def scenario() -> None:
        await rig.intake.on_dispatch(an_event())
        await rig.scheduler.drain()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (rig.outbox.sent_texts(), len(rig.capture.store.pending_captures())) == (
        ["📥 Saved — I'll file it once the AI is reachable."],
        1,
    )


def test_a_question_creates_no_item_and_goes_to_the_assistant_without_a_reply_from_stash() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer(route="request"))

    async def scenario() -> None:
        await rig.intake.on_dispatch(an_event(text=QUESTION))
        await rig.scheduler.drain()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (rig.assistant.asked, rig.capture.store.list_items(), rig.outbox.sent) == (
        [(QUESTION, Chat(chat_id=OWNER_ID, user_id=OWNER_ID))],
        [],
        [],
    )


def test_when_the_raw_save_fails_the_owner_is_told_to_send_it_again_and_the_hook_skips() -> None:
    # Setup
    rig = build_hermes_rig(
        answer=a_filing_answer(),
        wrap=lambda inner: RaisingIntake(inner, on_receive=SaveFailed("disk full")),
    )

    async def scenario() -> dict[str, str]:
        verdict = await rig.intake.on_dispatch(an_event())
        await rig.scheduler.drain()
        return verdict

    # Execute
    verdict = asyncio.run(scenario())

    # Assert
    assert (verdict, rig.outbox.sent_texts()) == (
        SKIP,
        ["⚠️ I could not save that message — please send it again."],
    )


def test_when_filing_raises_nothing_is_sent_and_the_capture_stays_pending() -> None:
    # Setup
    rig = build_hermes_rig(
        answer=a_filing_answer(),
        wrap=lambda inner: RaisingIntake(inner, on_process=FilingExploded("boom")),
    )

    async def scenario() -> None:
        await rig.intake.on_dispatch(an_event())
        await rig.scheduler.drain()

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (rig.outbox.sent, len(rig.capture.store.pending_captures())) == ([], 1)
