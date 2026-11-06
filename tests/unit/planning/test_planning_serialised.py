from builders import BASE
from capture_builders import sequential_ids
from fakes.fake_step_proposals import FakeStepProposals
from fakes.lingering_step_store import LingeringStepStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_builders import a_step
from threads import (
    OVERLAP_GRACE_SECONDS,
    THREAD_TIMEOUT_SECONDS,
    await_signal,
    run_concurrently,
    start,
)

from stash.planning import Planning

SIMULTANEOUS_ADDS = 2


def planning_over_a_lingering_store() -> tuple[LingeringStepStore, Planning]:
    store = LingeringStepStore(OVERLAP_GRACE_SECONDS)
    stored_date_night(store)
    return store, planning_over(store, FakeStepProposals(), lambda: BASE, sequential_ids())


def test_two_simultaneous_added_steps_get_distinct_positions() -> None:
    # Setup
    store, planning = planning_over_a_lingering_store()
    store.linger_on_next_read()

    # Execute
    errors = run_concurrently(
        SIMULTANEOUS_ADDS,
        lambda worker: planning.add_step(DATE_NIGHT_ID, f"Step {worker}", lead_days=worker),
    )

    # Assert
    assert (errors, sorted(step.position for step in store.steps_for(DATE_NIGHT_ID))) == (
        [],
        [0, 1],
    )


def test_a_step_added_while_the_proposed_steps_are_confirmed_survives_with_the_confirmations() -> (
    None
):
    # Setup
    store, planning = planning_over_a_lingering_store()
    store.save_steps(DATE_NIGHT_ID, [a_step(id="s1", item_id=DATE_NIGHT_ID, confirmed=False)])
    store.linger_on_next_read()
    confirming = start(lambda: planning.confirm_all(DATE_NIGHT_ID))
    await_signal(store.lingering)

    # Execute
    planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)
    confirming.join(THREAD_TIMEOUT_SECONDS)

    # Assert
    assert [(step.text, step.confirmed) for step in store.steps_for(DATE_NIGHT_ID)] == [
        ("Book the table", True),
        ("Buy tickets", True),
    ]
