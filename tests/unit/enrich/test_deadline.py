import logging
import math
import threading

import pytest
from fakes.hung_link_inspector import HungLinkInspector
from fakes.link_inspector import FakeLinkInspector
from link_builders import VIDEO_URL, a_link_info
from log_records import recording_logs

from stash.enrich.deadline import DeadlineInspector
from stash.enrich.links import LinkInfo

GENEROUS_DEADLINE_SECONDS = 5.0
SHORT_DEADLINE_SECONDS = 0.001
RELEASE_AFTER_SECONDS = 0.002
SECRET_URL = "https://example.com/private/path?token=sk-fake-123"


class FailingInspector:
    def inspect(self, url: str) -> LinkInfo:
        raise RuntimeError("extractor exploded")


def test_an_inspection_that_finishes_in_time_returns_the_inner_result() -> None:
    # Setup
    described = a_link_info()
    inspector = DeadlineInspector(
        FakeLinkInspector({VIDEO_URL: described}), GENEROUS_DEADLINE_SECONDS
    )

    # Execute
    info = inspector.inspect(VIDEO_URL)

    # Assert
    assert info == described


def test_an_inspection_that_finishes_a_moment_after_it_started_is_waited_for() -> None:
    # Setup
    described = a_link_info()
    slow = HungLinkInspector(described)
    threading.Timer(RELEASE_AFTER_SECONDS, slow.release.set).start()

    # Execute
    info = DeadlineInspector(slow, GENEROUS_DEADLINE_SECONDS).inspect(VIDEO_URL)

    # Assert
    assert info == described


def test_an_inspection_that_hangs_returns_unknown() -> None:
    # Setup
    hung = HungLinkInspector()

    # Execute
    info = DeadlineInspector(hung, SHORT_DEADLINE_SECONDS).inspect(VIDEO_URL)
    hung.release.set()

    # Assert
    assert info == LinkInfo.unknown(VIDEO_URL)


def test_the_abandoned_worker_cannot_keep_the_interpreter_alive() -> None:
    # Setup
    hung = HungLinkInspector()

    # Execute
    DeadlineInspector(hung, SHORT_DEADLINE_SECONDS).inspect(VIDEO_URL)
    daemon = hung.ran_in_a_daemon_thread()
    hung.release.set()

    # Assert
    assert daemon is True


def test_a_hung_inspection_does_not_stop_the_next_link_being_inspected() -> None:
    # Setup
    described = a_link_info()
    hung = HungLinkInspector()
    first = DeadlineInspector(hung, SHORT_DEADLINE_SECONDS)
    second = DeadlineInspector(FakeLinkInspector({VIDEO_URL: described}), GENEROUS_DEADLINE_SECONDS)
    first.inspect("https://example.com/slow")

    # Execute
    info = second.inspect(VIDEO_URL)
    hung.release.set()

    # Assert
    assert info == described


def test_giving_up_is_logged_at_warning_with_the_host_only() -> None:
    # Setup
    hung = HungLinkInspector()
    inspector = DeadlineInspector(hung, SHORT_DEADLINE_SECONDS)

    # Execute
    with recording_logs("stash.enrich.deadline") as recorder:
        inspector.inspect(SECRET_URL)
    hung.release.set()

    # Assert
    assert recorder.entries() == [
        (logging.WARNING, "link inspection gave up after 0.001 seconds: host example.com")
    ]


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
