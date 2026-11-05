import asyncio

from app_builders import an_app, stored
from builders import BASE, a_capture, an_item, minutes_after
from capture_builders import FORCED_QUESTION, a_filing_answer, a_message
from capture_rig import build_rig
from hermes_registration_rig import register_stash
from hermes_rig import app_over, called

from stash.domain import ItemType, Stage


def test_list_prints_the_newest_items_as_type_title_and_stage() -> None:
    # Setup
    older = an_item(
        id="i1",
        capture_id="c1",
        item_type=ItemType.PLACE,
        title="Ichiran ramen",
        stage=Stage.WANT_TO,
        created_at=BASE,
    )
    newer = an_item(
        id="i2",
        capture_id="c2",
        item_type=ItemType.RECIPE,
        title="Miso soup",
        stage=Stage.INBOX,
        created_at=minutes_after(5),
    )
    plugin = register_stash(an_app(store=stored(older, newer)))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["list"], ""))

    # Assert
    assert text.splitlines() == ["Recipes · Miso soup · Inbox", "Places · Ichiran ramen · Want to"]


def test_gpu_off_status_and_on_answer_and_act_as_the_stash_gpu_command_does() -> None:
    # Setup
    plugin = register_stash(an_app())

    async def scenario() -> list[str]:
        return [
            await called(plugin.ctx.commands["gpu"], argument)
            for argument in ("off", "status", "on", "status")
        ]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert answers == [
        "GPU switched off until 08:00",
        "GPU busy — turned off until 08:00",
        "GPU switched on",
        "GPU free — GPU is free",
    ]


def test_retry_files_the_pending_captures_one_line_each_and_then_finds_nothing_pending() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    rig.store.add_capture(a_capture(text="Ichiran ramen in Fukuoka"))
    plugin = register_stash(app_over(rig))

    async def scenario() -> list[str]:
        return [await called(plugin.ctx.commands["retry"], "") for _ in range(2)]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert answers == ["filed — Places · Ichiran ramen · Want to", "Nothing pending."]


def test_retry_command_answers_a_pending_question_as_a_request_and_asks_the_ai_nothing() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    rig.pipeline.receive(a_message(FORCED_QUESTION))
    plugin = register_stash(app_over(rig))

    async def scenario() -> list[str]:
        return [await called(plugin.ctx.commands["retry"], "") for _ in range(2)]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert (answers, rig.model.calls, rig.store.list_items()) == (
        [f"request — {FORCED_QUESTION}", "Nothing pending."],
        [],
        [],
    )
