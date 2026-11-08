import asyncio
import inspect

from capture_rig import build_rig
from hermes_events import SKIP, an_event
from hermes_registration_rig import OpenedApps, register_stash_over
from hermes_rig import instant_bursts

from stash.hermes_adapter.plugin import PROCESS_STATE, register

QUESTION_BUTTON = "That was a question →"
NEW_OWNER_ID = "77"


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
