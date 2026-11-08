import pytest
from digest_builders import (
    DIGEST_AT,
    a_digest_builder,
    a_due_digest,
)
from fakes.store_factories import FreshStore

from stash.nudges.digest_builder import DIGEST_CONTEXT


def test_the_picks_context_asks_for_things_worth_doing_in_the_coming_week() -> None:
    # Assert
    assert DIGEST_CONTEXT == "Pick things worth doing in the coming week."


def test_building_with_a_now_that_has_no_time_zone_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="now"):
        a_digest_builder(FreshStore()).build(a_due_digest(), DIGEST_AT.replace(tzinfo=None))
