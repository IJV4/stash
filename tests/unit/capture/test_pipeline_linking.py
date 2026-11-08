import logging

import pytest
from capture_builders import a_filing_answer, a_message, a_pipeline, an_agent_message
from capture_narrowing import handle_filed
from capture_rig import CaptureRig, build_rig
from fakes.capture_filer import FakeCaptureFiler
from fakes.failing_link_store import FailingLinkStore
from fakes.failing_status_store import FailingStatusStore, StatusWriteFailed
from fakes.link_inspector import FakeLinkInspector
from fakes.recording_linker import RecordingLinker
from fakes.store_factories import FreshStore
from log_records import recording_logs

from stash.capture import Filed

PEOPLE_FILING = a_filing_answer(people=["Ana"])


def a_rig_whose_linking_fails() -> CaptureRig:
    rig = build_rig(answer=PEOPLE_FILING, store=FailingLinkStore())
    rig.people.add("Ana")
    return rig


def test_an_item_filed_from_an_agent_capture_is_handed_to_the_linker() -> None:
    # Setup
    linker = RecordingLinker()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), FakeCaptureFiler(), linker=linker)

    # Execute
    result = pipeline.handle(an_agent_message())

    # Assert
    assert isinstance(result, Filed)
    assert linker.linked == [result.item]


def test_resuming_after_a_crash_before_the_status_write_does_not_link_the_item_again() -> None:
    # Setup
    store = FailingStatusStore()
    linker = RecordingLinker()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler(), linker=linker)
    store.fail_next_status_write = True
    with pytest.raises(StatusWriteFailed):
        pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert len(linker.linked) == 1


def test_a_linking_failure_is_logged_as_an_error() -> None:
    # Setup
    rig = a_rig_whose_linking_fails()

    # Execute
    with recording_logs("stash.capture") as recorder:
        handle_filed(rig, a_message())

    # Assert
    assert [level for level, _ in recorder.entries()] == [logging.ERROR]


def test_a_linking_failure_still_files_and_returns_the_item() -> None:
    # Setup
    rig = a_rig_whose_linking_fails()

    # Execute
    filed = handle_filed(rig, a_message())

    # Assert
    assert rig.store.list_items() == [filed.item]


def test_a_linking_failure_still_marks_the_capture_filed() -> None:
    # Setup
    rig = a_rig_whose_linking_fails()

    # Execute
    handle_filed(rig, a_message())

    # Assert
    assert rig.store.pending_captures() == []
