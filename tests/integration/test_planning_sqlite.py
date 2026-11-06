from pathlib import Path

import pytest
from fakes.chat_model import FakeChatModel
from fakes.store_factories import opened, sqlite_store
from planning_builders import DATE_NIGHT_ID, steps_reply, stored_date_night
from planning_rig import a_planning

from stash.planning import PlanningRefused


@pytest.mark.integration
def test_proposed_steps_read_back_from_sqlite_unconfirmed_and_not_open() -> None:
    # Setup
    with sqlite_store() as store:
        stored_date_night(store)
        planning = a_planning(store, FakeChatModel(steps_reply(3)))

        # Execute
        proposal = planning.propose_for(DATE_NIGHT_ID)

        # Assert
        assert (store.steps_for(DATE_NIGHT_ID), store.open_confirmed_steps()) == (
            list(proposal.steps),
            [],
        )


@pytest.mark.integration
def test_confirming_over_sqlite_makes_every_step_open() -> None:
    # Setup
    with sqlite_store() as store:
        stored_date_night(store)
        planning = a_planning(store, FakeChatModel(steps_reply(3)))
        planning.propose_for(DATE_NIGHT_ID)

        # Execute
        confirmed = planning.confirm_all(DATE_NIGHT_ID)

        # Assert
        assert store.open_confirmed_steps() == list(confirmed)


@pytest.mark.integration
def test_discarding_unconfirmed_steps_over_sqlite_removes_them() -> None:
    # Setup
    with sqlite_store() as store:
        stored_date_night(store)
        planning = a_planning(store, FakeChatModel(steps_reply(3)))
        planning.propose_for(DATE_NIGHT_ID)

        # Execute
        planning.discard(DATE_NIGHT_ID)

        # Assert
        assert store.steps_for(DATE_NIGHT_ID) == []


@pytest.mark.integration
def test_discarding_after_confirming_over_sqlite_keeps_the_confirmed_steps() -> None:
    # Setup
    with sqlite_store() as store:
        stored_date_night(store)
        planning = a_planning(store, FakeChatModel(steps_reply(3)))
        planning.propose_for(DATE_NIGHT_ID)
        confirmed = planning.confirm_all(DATE_NIGHT_ID)

        # Execute
        planning.discard(DATE_NIGHT_ID)

        # Assert
        assert store.steps_for(DATE_NIGHT_ID) == list(confirmed)


@pytest.mark.integration
def test_proposing_again_over_sqlite_is_refused_and_keeps_the_steps() -> None:
    # Setup
    with sqlite_store() as store:
        stored_date_night(store)
        planning = a_planning(store, FakeChatModel(steps_reply(3)))
        proposal = planning.propose_for(DATE_NIGHT_ID)

        # Execute
        with pytest.raises(PlanningRefused):
            planning.propose_for(DATE_NIGHT_ID)

        # Assert
        assert store.steps_for(DATE_NIGHT_ID) == list(proposal.steps)


@pytest.mark.integration
def test_a_decline_survives_closing_and_reopening_the_sqlite_store(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as store:
        item = stored_date_night(store)
        a_planning(store, FakeChatModel(steps_reply(3))).discard(DATE_NIGHT_ID)

    # Execute
    with opened(path) as reopened:
        needed = a_planning(reopened, FakeChatModel(steps_reply(3))).needs_proposal(item)

    # Assert
    assert needed is False
