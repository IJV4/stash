import asyncio

from capture_builders import a_filing_answer, button_data
from hermes_events import OWNER_ID, STRANGER_ID
from hermes_rig import CONFIRMATION_MESSAGE_ID, a_press, build_hermes_rig

from stash.capture.callbacks import FixAction, FixKind
from stash.hermes_adapter.events import Chat

QUESTION = "what can I do Saturday afternoon?"
GONE = "That item no longer exists."
FORGED_ITEM_ID = "f" * 32


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
    rig = build_hermes_rig(
        answer=a_filing_answer(route="unsure", item_type="other", details={}),
    )

    async def scenario() -> None:
        confirmation = await rig.confirmation_for(QUESTION)
        await rig.callbacks.on_press(a_press(button_data(confirmation, "That was a question →")))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert rig.assistant.asked == [(QUESTION, Chat(chat_id=OWNER_ID, user_id=OWNER_ID))]


def test_a_press_from_anybody_but_the_owner_changes_and_asks_nothing() -> None:
    # Setup
    rig = build_hermes_rig(
        answer=a_filing_answer(route="unsure", item_type="other", details={}),
    )

    async def scenario() -> None:
        confirmation = await rig.confirmation_for(QUESTION)
        data = button_data(confirmation, "That was a question →")
        await rig.callbacks.on_press(a_press(data, user_id=STRANGER_ID))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (rig.assistant.asked, rig.outbox.edited, len(rig.capture.store.list_items())) == (
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
