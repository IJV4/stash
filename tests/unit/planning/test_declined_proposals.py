import logging

import pytest
from fakes.chat_model import FakeChatModel
from fakes.store_factories import FreshStore
from log_records import recording_logs
from planning_builders import (
    DATE_NIGHT_ID,
    a_raw_step,
    stored_date_night,
)
from planning_rig import a_planning

from stash.llm import LlmBadOutput
from stash.planning import ProposalUnusable

SERVICE_LOGGER = "stash.planning.service"
MODEL_OUTPUT = "sk-secret-model-output {not json"


def test_after_an_answer_whose_every_step_is_unusable_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    unusable = {"steps": [a_raw_step(lead_days=True), a_raw_step(lead_days=False)]}
    planning = a_planning(store, FakeChatModel(unusable))

    # Execute
    with pytest.raises(ProposalUnusable):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_after_unusable_model_output_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(error=LlmBadOutput("not json")))

    # Execute
    with pytest.raises(ProposalUnusable):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_an_unusable_answer_is_logged_naming_only_the_error_class() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    planning = a_planning(store, FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))

    # Execute
    with recording_logs(SERVICE_LOGGER) as recorder, pytest.raises(ProposalUnusable):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert recorder.entries() == [
        (logging.WARNING, "step model gave unusable output: LlmBadOutput")
    ]
