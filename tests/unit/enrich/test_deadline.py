import math

import pytest
from fakes.link_inspector import FakeLinkInspector
from link_builders import VIDEO_URL

from stash.enrich.deadline import DeadlineInspector
from stash.enrich.links import LinkInfo

GENEROUS_DEADLINE_SECONDS = 5.0
SHORT_DEADLINE_SECONDS = 0.001


class FailingInspector:
    def inspect(self, url: str) -> LinkInfo:
        raise RuntimeError("extractor exploded")


def test_an_error_from_the_inner_inspector_reaches_the_caller() -> None:
    # Setup
    inspector = DeadlineInspector(FailingInspector(), GENEROUS_DEADLINE_SECONDS)

    # Execute / Assert
    with pytest.raises(RuntimeError, match="extractor exploded"):
        inspector.inspect(VIDEO_URL)


@pytest.mark.parametrize("deadline", [0, -1, math.nan, math.inf, -math.inf])
def test_a_deadline_that_is_not_a_positive_finite_number_is_rejected(deadline: float) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="deadline_seconds"):
        DeadlineInspector(FakeLinkInspector(), deadline)
