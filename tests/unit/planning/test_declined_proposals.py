from fakes.chat_model import FakeChatModel
from fakes.store_factories import FreshStore
from planning_builders import (
    DATE_NIGHT_ID,
    a_raw_step,
    stored_date_night,
)
from planning_rig import a_planning

from stash.llm import LlmBadOutput


def test_after_an_answer_whose_every_step_is_unusable_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    unusable = {"steps": [a_raw_step(lead_days=True), a_raw_step(lead_days=False)]}
    planning = a_planning(store, FakeChatModel(unusable))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_after_unusable_model_output_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(error=LlmBadOutput("not json")))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False
