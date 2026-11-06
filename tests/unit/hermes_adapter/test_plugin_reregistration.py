import asyncio
import inspect

from builders import stored_item
from capture_builders import QUESTION, a_request_answer, an_unsure_answer
from capture_rig import build_rig
from config_builders import a_stash_config
from fakes.fake_suggestion_desk import FakeSuggestionDesk
from fakes.recording_loader import RecordingLoader
from hermes_events import SKIP, an_event
from hermes_registration_rig import OpenedApps, register_stash, register_stash_over
from hermes_rig import app_over, called, instant_bursts, until

from stash.domain import Stage
from stash.hermes_adapter.plugin import PROCESS_STATE, register
from stash.suggestions import Picked

QUESTION_BUTTON = "That was a question →"
NEW_OWNER_ID = "77"


def test_a_second_register_builds_no_second_app() -> None:
    # Setup
    apps = OpenedApps(build_rig())
    plugin = register_stash_over(apps)

    # Execute
    plugin.register_again()

    # Assert
    assert apps.built == 1


def test_a_second_register_does_not_read_the_configuration_again() -> None:
    # Setup
    loader = RecordingLoader(a_stash_config())
    plugin = register_stash_over(OpenedApps(build_rig()), load=loader)

    # Execute
    plugin.register_again()

    # Assert
    assert len(loader.calls) == 1


def test_a_second_register_adds_no_second_exit_hook() -> None:
    # Setup
    plugin = register_stash_over(OpenedApps(build_rig()))

    # Execute
    plugin.register_again()

    # Assert
    assert len(plugin.exits) == 1


def test_a_second_register_registers_the_hook_the_commands_and_the_tools_in_its_context() -> None:
    # Setup
    plugin = register_stash_over(OpenedApps(build_rig()))

    # Execute
    reloaded = plugin.reloaded().ctx

    # Assert
    assert (sorted(reloaded.hooks), sorted(reloaded.commands), sorted(reloaded.tools)) == (
        sorted(plugin.ctx.hooks),
        sorted(plugin.ctx.commands),
        sorted(plugin.ctx.tools),
    )


def test_a_second_register_registers_all_fourteen_tools_in_its_context() -> None:
    # Setup
    plugin = register_stash_over(OpenedApps(build_rig()))

    # Execute
    reloaded = plugin.reloaded().ctx

    # Assert
    assert len(reloaded.tools) == 14


def test_a_lifecycle_tool_registered_by_a_second_register_acts_on_the_same_store() -> None:
    # Setup
    rig = build_rig()
    store = rig.store
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    plugin = register_stash(app_over(rig))
    reloaded = plugin.reloaded().ctx

    # Execute
    reloaded.tools["stash_complete"].handler({"item_id": "w1", "rating": 2})

    # Assert
    assert [outcome.rating for outcome in store.outcomes_for("w1")] == [2]


def test_a_step_tool_registered_by_a_second_register_acts_on_the_same_store() -> None:
    # Setup
    rig = build_rig()
    store = rig.store
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    plugin = register_stash(app_over(rig))
    reloaded = plugin.reloaded().ctx

    # Execute
    reloaded.tools["stash_add_step"].handler({"item_id": "w1", "text": "Book", "lead_days": 2})

    # Assert
    assert [step.text for step in store.steps_for("w1")] == ["Book"]


def test_the_suggest_command_registered_by_a_second_register_asks_the_same_suggestions() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked(()))
    plugin = register_stash(app_over(build_rig(), suggestions=desk))
    reloaded = plugin.reloaded().ctx

    # Execute
    asyncio.run(called(reloaded.commands["suggest"], "at home"))

    # Assert
    assert desk.asked == [("at home", 3)]


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


def test_registrations_with_different_states_open_an_app_each() -> None:
    # Setup
    apps = OpenedApps(build_rig())
    register_stash_over(apps)

    # Execute
    register_stash_over(apps)

    # Assert
    assert apps.built == 2


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
