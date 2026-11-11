import asyncio
import logging

import pytest
from capture_builders import (
    BARE_QUESTION_MARK,
    DEFERRED_REPLY,
    FORCED_QUESTION,
    INDENTED_FORCED_QUESTION,
    LINK_WITH_A_QUERY,
    a_filing_answer,
)
from fakes.racing_retry_intake import RacingRetryIntake
from fakes.raising_intake import RaisingIntake
from hermes_events import ALLOW, SKIP, an_event
from hermes_rig import build_hermes_rig
from log_records import recording_logs

from stash.capture import CaptureIntake, IsRequest
from stash.domain import CaptureStatus

INTAKE_LOGGER = "stash.hermes_adapter.intake"


class FilingExploded(Exception):
    pass


@pytest.mark.parametrize("text", [BARE_QUESTION_MARK, INDENTED_FORCED_QUESTION])
def test_a_message_starting_with_a_question_mark_is_a_request_without_asking_the_ai(
    text: str,
) -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event(text=text)))

    # Assert
    assert {
        "verdict": verdict,
        "model_calls": rig.capture.model.calls,
        "capture_statuses": rig.capture_statuses(),
        "items": rig.capture.store.list_items(),
    } == {
        "verdict": ALLOW,
        "model_calls": [],
        "capture_statuses": [CaptureStatus.REQUEST],
        "items": [],
    }


def test_a_link_containing_a_question_mark_is_classified_and_filed_not_forced() -> None:
    # Setup
    rig = build_hermes_rig(answer=a_filing_answer())

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event(text=LINK_WITH_A_QUERY)))

    # Assert
    assert (verdict, len(rig.capture.model.calls), len(rig.capture.store.list_items())) == (
        SKIP,
        1,
        1,
    )


def test_a_forced_question_whose_processing_raises_is_allowed_and_retried_as_a_request() -> None:
    # Setup
    rig = build_hermes_rig(
        answer=a_filing_answer(),
        wrap=lambda inner: RaisingIntake(inner, on_process=FilingExploded("boom")),
    )

    # Execute
    with recording_logs(INTAKE_LOGGER) as logs:
        [verdict] = asyncio.run(rig.deliver(an_event(text=FORCED_QUESTION)))
    pending = len(rig.capture.store.pending_captures())
    retried = rig.capture.pipeline.retry_pending()

    # Assert
    assert {
        "verdict": verdict,
        "logs": logs.entries(),
        "sent": rig.outbox.sent_texts(),
        "pending": pending,
        "retried": [type(result) for result in retried],
        "items": rig.capture.store.list_items(),
    } == {
        "verdict": ALLOW,
        "logs": [(logging.ERROR, f"processing capture {1:032x} failed")],
        "sent": [DEFERRED_REPLY],
        "pending": 1,
        "retried": [IsRequest],
        "items": [],
    }


def test_a_retry_racing_the_hook_on_a_forced_question_files_nothing_and_hook_allows_once() -> None:
    # Setup
    racing: list[RacingRetryIntake] = []

    def race(inner: CaptureIntake) -> CaptureIntake:
        wrapper = RacingRetryIntake(inner)
        racing.append(wrapper)
        return wrapper

    rig = build_hermes_rig(answer=a_filing_answer(), wrap=race)

    # Execute
    [verdict] = asyncio.run(rig.deliver(an_event(text=FORCED_QUESTION)))

    # Assert
    assert {
        "verdict": verdict,
        "retried": [[type(result) for result in results] for results in racing[0].retried],
        "model_calls": rig.capture.model.calls,
        "items": rig.capture.store.list_items(),
        "statuses": rig.capture_statuses(),
        "injected": rig.ctx.injected,
        "sent": rig.outbox.sent,
    } == {
        "verdict": ALLOW,
        "retried": [[IsRequest]],
        "model_calls": [],
        "items": [],
        "statuses": [CaptureStatus.REQUEST],
        "injected": [],
        "sent": [],
    }
