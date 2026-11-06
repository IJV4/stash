from datetime import timedelta

import pytest
from builders import stored
from digest_builders import (
    DIGEST_AT,
    SAIL_ID,
    a_digest_builder,
    a_forgotten_sail,
    a_new_want_to,
    a_step_the_day_before_the_date_night,
    stored_every_section,
)
from fakes.store_factories import sqlite_store
from nudge_builders import (
    FRIDAY,
    SATURDAY,
    a_nudge_schedule,
    a_nudger,
    a_planned_date_night,
    only,
)

from stash.nudges import NudgeMessage, WeeklyDigest
from stash.nudges.digest import DigestSections, UpcomingItem, UpcomingStep
from stash.store import Store

SIX_DIGESTS_SPAN = timedelta(weeks=5, days=1)


def sections_built_over(store: Store) -> DigestSections:
    [due] = only(WeeklyDigest, a_nudger(store).due(DIGEST_AT))
    return a_digest_builder(store).build(due, DIGEST_AT).sections


@pytest.mark.integration
def test_over_sqlite_a_digest_has_every_section_a_week_of_items_gives() -> None:
    # Setup
    date_night = a_planned_date_night()
    expected = DigestSections(
        new_items=(
            a_new_want_to("carbonara", 2, title="Pasta carbonara"),
            a_new_want_to("ramen", 3, title="Ramen"),
        ),
        forgotten=(a_forgotten_sail(),),
        upcoming=(
            UpcomingStep(FRIDAY, date_night, a_step_the_day_before_the_date_night()),
            UpcomingItem(SATURDAY, date_night),
        ),
        picks=(),
    )
    with sqlite_store() as store:
        stored_every_section(store)

        # Execute
        sections = sections_built_over(store)

    # Assert
    assert sections == expected


@pytest.mark.integration
def test_over_sqlite_a_forgotten_item_is_absent_for_four_digests_after_the_one_that_showed_it() -> (
    None
):
    # Setup
    with sqlite_store() as store:
        stored(store, a_forgotten_sail())
        nudger = a_nudger(store)
        builder = a_digest_builder(store)
        shown: list[list[str]] = []

        # Execute
        for instant in a_nudge_schedule().digest_instants_between(
            DIGEST_AT, DIGEST_AT + SIX_DIGESTS_SPAN
        ):
            [due] = only(WeeklyDigest, nudger.due(instant))
            digest = builder.build(due, instant)
            shown.append([item.id for item in digest.sections.forgotten])
            nudger.mark_sent(NudgeMessage((digest,), catch_up=False), instant)

    # Assert
    assert shown == [[SAIL_ID], [], [], [], [], [SAIL_ID]]
