import asyncio
from collections.abc import Callable

import pytest
from capture_builders import DEFERRED_REPLY, QUESTION, a_filing_answer, a_request_answer
from fakes.raising_intake import RaisingIntake
from hermes_ctx_builders import a_hermes_context
from hermes_events import ALLOW, SKIP, STRANGER_ID, an_event
from hermes_registration_rig import register_stash
from hermes_rig import HermesRig, app_over, build_hermes_rig, called

from stash.llm import LlmUnavailable


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
        [DEFERRED_REPLY],
        1,
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


def test_when_filing_raises_the_owner_is_told_it_is_saved_and_the_capture_stays_pending() -> None:
    # Setup
    rig = build_hermes_rig(
        answer=a_filing_answer(),
        wrap=lambda inner: RaisingIntake(inner, on_process=FilingExploded("boom")),
    )

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event()))

    # Assert
    assert (verdict, rig.outbox.sent_texts(), len(rig.capture.store.pending_captures())) == (
        SKIP,
        [DEFERRED_REPLY],
        1,
    )


@pytest.mark.parametrize(
    ("build", "gpu_busy_while_capturing"),
    [
        pytest.param(lambda: build_hermes_rig(answer=a_filing_answer()), True, id="gpu-busy"),
        pytest.param(
            lambda: build_hermes_rig(outcomes=[LlmUnavailable("down"), a_filing_answer()]),
            False,
            id="ai-down",
        ),
        pytest.param(
            lambda: build_hermes_rig(
                answer=a_filing_answer(),
                wrap=lambda inner: RaisingIntake(inner, on_process=FilingExploded("boom")),
            ),
            False,
            id="filing-raises",
        ),
    ],
)
def test_a_deferred_capture_gets_the_one_reply_and_stash_retry_then_files_it(
    build: Callable[[], HermesRig], gpu_busy_while_capturing: bool
) -> None:
    # Setup
    rig = build()
    rig.capture.busy.busy = gpu_busy_while_capturing

    # Execute
    asyncio.run(rig.deliver(an_event()))
    rig.capture.busy.busy = False
    plugin = register_stash(app_over(rig.capture), a_hermes_context(reserved={"retry"}))
    answer = asyncio.run(called(plugin.ctx.commands["stash-retry"], ""))

    # Assert
    assert (rig.outbox.sent_texts(), answer) == (
        [DEFERRED_REPLY],
        "filed — Places · Ichiran ramen · Want to",
    )


def test_a_question_is_allowed_through_to_the_agent_and_creates_no_item_and_no_reply() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_request_answer())

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event(text=QUESTION)))

    # Assert
    assert {
        "verdict": verdict,
        "injected": rig.ctx.injected,
        "refused": rig.ctx.refused,
        "items": rig.capture.store.list_items(),
        "sent": rig.outbox.sent,
    } == {"verdict": ALLOW, "injected": [], "refused": [], "items": [], "sent": []}


def test_a_burst_with_one_question_allows_it_and_confirms_the_four_captures_together() -> None:
    # Setup
    rig = build_hermes_rig(
        outcomes=[
            a_filing_answer(title="Ramen"),
            a_filing_answer(title="Pasta"),
            a_request_answer(),
            a_filing_answer(title="Tacos"),
            a_filing_answer(title="Pho"),
        ]
    )
    events = [an_event(text=f"which message {n}?", message_id=f"m{n}") for n in range(5)]

    # Execute
    verdicts = asyncio.run(rig.deliver(*events))

    # Assert
    assert (verdicts, [text.splitlines()[0] for text in rig.outbox.sent_texts()]) == (
        [SKIP, SKIP, ALLOW, SKIP, SKIP],
        ["✅ Saved 4 items:"],
    )


def test_when_the_ai_goes_down_after_the_raw_save_the_hook_skips_and_the_agent_gets_nothing() -> (
    None
):
    # Setup
    rig = build_hermes_rig(outcomes=[LlmUnavailable("connection refused")])

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event(text=QUESTION)))

    # Assert
    assert (
        verdict,
        len(rig.capture.store.pending_captures()),
        rig.ctx.injected,
        rig.ctx.refused,
    ) == (SKIP, 1, [], [])


def test_a_redelivered_question_reaches_the_agent_only_once() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_request_answer())
    redelivery = [an_event(text=QUESTION, message_id="m1")] * 2

    # Execute
    verdicts = asyncio.run(rig.deliver(*redelivery))

    # Assert
    assert verdicts == [ALLOW, SKIP]


def test_control_characters_in_the_models_answer_never_reach_the_stored_item_or_the_reply() -> None:
    # Setup
    answer = a_filing_answer(
        title="Ramen\x1b[2J\x07 spot",
        details={"city": "To\x1b]52;c;ZmFrZQ==\x07kyo", "note": "\x1b\x07"},
    )
    rig = build_hermes_rig(answer=answer)

    # Execute
    asyncio.run(rig.deliver(an_event()))

    # Assert
    [item] = rig.capture.store.list_items()
    assert (rig.outbox.sent_texts(), item.title, dict(item.details)) == (
        ["✅ Places · To ]52;c;ZmFrZQ== kyo · Want to"],
        "Ramen [2J spot",
        {"city": "To ]52;c;ZmFrZQ== kyo"},
    )
