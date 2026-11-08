import asyncio
import inspect

from capture_builders import QUESTION, a_request_answer, an_unsure_answer
from capture_rig import build_rig
from hermes_events import SKIP, an_event
from hermes_registration_rig import OpenedApps, register_stash, register_stash_over
from hermes_rig import app_over, instant_bursts, until

from stash.hermes_adapter.plugin import PROCESS_STATE, register

QUESTION_BUTTON = "That was a question →"
NEW_OWNER_ID = "77"


def test_a_press_after_a_second_register_injects_into_the_newest_context() -> None:
    # Setup
    rig = build_rig(outcomes=[a_request_answer(), an_unsure_answer()])
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()
    second = plugin.reloaded()

    async def scenario() -> None:
        await second.dispatch(an_event(text="what is on my list?", message_id="q1"))
        await second.dispatch(an_event(text=QUESTION, message_id="q2"))
        await until(lambda: plugin.bot.sent)
        await plugin.press(plugin.sent_button_data(QUESTION_BUTTON))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (
        [message.content for message in second.ctx.injected],
        plugin.ctx.injected,
    ) == ([QUESTION], [])


def test_register_defaults_to_the_process_wide_adapter_state() -> None:
    # Setup
    parameter = inspect.signature(register).parameters["state"]

    # Execute
    default = parameter.default

    # Assert
    assert default is PROCESS_STATE


def test_a_second_register_with_a_new_allowed_user_list_answers_the_new_owner() -> None:
    # Setup
    plugin = register_stash_over(OpenedApps(build_rig(), burst_factory=instant_bursts))
    reloaded = plugin.reloaded(owner_ids=NEW_OWNER_ID)

    # Execute
    verdict = asyncio.run(reloaded.dispatch(an_event(user_id=NEW_OWNER_ID)))

    # Assert
    assert verdict == SKIP
