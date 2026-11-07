import asyncio
from dataclasses import replace

from builders import PLANNED_FOR, an_item_at, stored
from capture_builders import (
    QUESTION,
    a_filing_answer,
    a_request_answer,
    an_unsure_answer,
    button_data,
    store_with_filed_item,
)
from fakes.busy_store import BusyStore
from fakes.changing_item_store import RETITLED_BY_ANOTHER_WRITER, ChangingItemStore
from fakes.recording_assistant import RecordingAssistant
from fakes.vanishing_item_store import VanishingItemStore
from hermes_events import OWNER_ID, STRANGER_ID, an_event
from hermes_rig import CONFIRMATION_MESSAGE_ID, a_press, build_button_rig, build_hermes_rig
from planning_builders import DATE_NIGHT_ID, stored_date_night
from step_builders import a_step

from stash.capture.callbacks import FixAction, FixKind, date_argument
from stash.domain import Stage
from stash.hermes_adapter.events import Chat

GONE = "That item no longer exists."
CHANGED = "That changed meanwhile — try again."
BUSY = "The stash is busy — try again in a moment."
FORGED_ITEM_ID = "f" * 32
APOLOGY_TEXT = (
    "I couldn't pass that on to the assistant. Send it again starting with ? and I'll hand it over."
)


def test_pressing_type_then_recipes_edits_the_same_message_to_the_updated_confirmation() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    async def scenario() -> None:
        confirmation = await rig.confirmation_for()
        await rig.callbacks.on_press(a_press(button_data(confirmation, "Type")))
        menu = rig.outbox.edited[-1].reply
        await rig.callbacks.on_press(a_press(button_data(menu, "Recipes")))

    # Execute
    asyncio.run(scenario())

    # Assert
    last = rig.outbox.edited[-1]
    assert (last.chat_id, last.message_id, last.reply.text) == (
        OWNER_ID,
        CONFIRMATION_MESSAGE_ID,
        "✅ Recipes · Tokyo · Want to",
    )


def test_pressing_that_was_a_question_hands_the_original_text_to_the_assistant() -> None:
    # Setup
    assistant = RecordingAssistant()
    rig = build_hermes_rig(answer=an_unsure_answer(), assistant=assistant)

    async def scenario() -> None:
        confirmation = await rig.confirmation_for(QUESTION)
        await rig.callbacks.on_press(a_press(button_data(confirmation, "That was a question →")))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert assistant.asked == [(QUESTION, Chat(chat_id=OWNER_ID, user_id=OWNER_ID))]


def test_a_press_from_anybody_but_the_owner_changes_and_asks_nothing() -> None:
    # Setup
    assistant = RecordingAssistant()
    rig = build_hermes_rig(answer=an_unsure_answer(), assistant=assistant)

    async def scenario() -> None:
        confirmation = await rig.confirmation_for(QUESTION)
        data = button_data(confirmation, "That was a question →")
        await rig.callbacks.on_press(a_press(data, user_id=STRANGER_ID))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (assistant.asked, rig.outbox.edited, len(rig.capture.store.list_items())) == (
        [],
        [],
        1,
    )


def test_a_stale_or_forged_press_edits_the_message_to_say_the_item_no_longer_exists() -> None:
    # Setup
    rig = build_hermes_rig()

    # Execute
    asyncio.run(
        rig.callbacks.on_press(a_press(FixAction(FixKind.TYPE_MENU, FORGED_ITEM_ID).encode()))
    )

    # Assert
    assert [(edit.message_id, edit.reply.text) for edit in rig.outbox.edited] == [
        (CONFIRMATION_MESSAGE_ID, GONE)
    ]


def test_pressing_that_was_a_question_with_no_admitted_message_in_the_chat_apologises() -> None:
    # Setup
    rig = build_hermes_rig(answer=an_unsure_answer())

    async def scenario() -> None:
        confirmation = await rig.confirmation_for(QUESTION)
        await rig.callbacks.on_press(a_press(button_data(confirmation, "That was a question →")))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (rig.outbox.sent_texts()[1:], rig.ctx.injected, len(rig.ctx.refused)) == (
        [APOLOGY_TEXT],
        [],
        1,
    )


def test_pressing_that_was_a_question_after_an_allowed_question_injects_the_text() -> None:
    # Setup
    rig = build_hermes_rig(outcomes=[a_request_answer(), an_unsure_answer()])

    async def scenario() -> None:
        await rig.deliver(an_event(text="what is on my list?", message_id="q1"))
        confirmation = await rig.confirmation_for(QUESTION)
        await rig.callbacks.on_press(a_press(button_data(confirmation, "That was a question →")))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert ([message.content for message in rig.ctx.injected], rig.ctx.refused) == ([QUESTION], [])


def test_pressing_didnt_happen_on_an_item_deleted_meanwhile_says_it_no_longer_exists() -> None:
    # Setup
    store = VanishingItemStore()
    stored(store, an_item_at(Stage.PLANNED))
    store.vanish_after_reading_item("i1")
    rig = build_button_rig(store)

    # Execute
    shown = rig.pressed(FixAction(FixKind.NOT_HAPPENED, "i1", date_argument(PLANNED_FOR)).encode())

    # Assert
    assert (shown, store.get_item("i1")) == (GONE, None)


def test_a_stage_press_on_an_item_changed_meanwhile_asks_to_try_again_and_keeps_the_change() -> (
    None
):
    # Setup
    store = ChangingItemStore()
    _, item = store_with_filed_item(store, stage=Stage.INBOX)
    store.change_after_reading_item("c1")
    rig = build_button_rig(store)

    # Execute
    shown = rig.pressed(FixAction(FixKind.SET_STAGE, "c1", Stage.DOING.value).encode())

    # Assert
    assert (shown, store.get_item("c1")) == (
        CHANGED,
        replace(item, title=RETITLED_BY_ANOTHER_WRITER),
    )


def test_pressing_done_while_the_store_is_busy_asks_to_try_again_in_a_moment() -> None:
    # Setup
    store = BusyStore()
    stored(store, an_item_at(Stage.DOING))
    rig = build_button_rig(store)

    # Execute
    shown = rig.pressed(FixAction(FixKind.DONE, "i1").encode())

    # Assert
    assert shown == BUSY


def test_pressing_looks_good_while_the_store_is_busy_asks_to_try_again_and_confirms_nothing() -> (
    None
):
    # Setup
    store = BusyStore()
    stored_date_night(store)
    store.save_step(a_step(item_id=DATE_NIGHT_ID))
    rig = build_button_rig(store)

    # Execute
    shown = rig.pressed(FixAction(FixKind.ACCEPT_STEPS, DATE_NIGHT_ID).encode())

    # Assert
    assert (shown, [step.confirmed for step in store.steps_for(DATE_NIGHT_ID)]) == (BUSY, [False])
