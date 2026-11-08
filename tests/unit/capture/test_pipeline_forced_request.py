import pytest
from builders import an_item
from capture_builders import (
    FORCED_QUESTION,
    FORCING_TEXTS,
    LINK_WITH_A_QUERY,
    a_message,
    a_pipeline,
    received,
)
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore

from stash.capture import Filed, IsRequest
from stash.domain import CaptureStatus


@pytest.mark.parametrize("text", FORCING_TEXTS)
def test_processing_a_text_starting_with_a_question_mark_returns_the_capture_as_a_request(
    text: str,
) -> None:
    # Setup
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), FakeCaptureFiler())
    capture = received(pipeline, text)

    # Execute
    result = pipeline.process(capture)

    # Assert
    assert result == IsRequest(capture.with_status(CaptureStatus.REQUEST))


@pytest.mark.parametrize("text", FORCING_TEXTS)
def test_processing_a_text_starting_with_a_question_mark_stores_the_capture_as_a_request(
    text: str,
) -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    capture = received(pipeline, text)

    # Execute
    pipeline.process(capture)

    # Assert
    assert store.get_capture(capture.id) == capture.with_status(CaptureStatus.REQUEST)


def test_processing_a_text_starting_with_a_question_mark_asks_the_ai_nothing() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = received(pipeline, f"? {LINK_WITH_A_QUERY}")

    # Execute
    pipeline.process(capture)

    # Assert
    assert filer.calls == []


def test_processing_a_text_starting_with_a_question_mark_inspects_no_link() -> None:
    # Setup
    inspector = FakeLinkInspector()
    pipeline = a_pipeline(FreshStore(), inspector, FakeCaptureFiler())
    capture = received(pipeline, f"? {LINK_WITH_A_QUERY}")

    # Execute
    pipeline.process(capture)

    # Assert
    assert inspector.inspected == []


def test_processing_a_text_starting_with_a_question_mark_creates_no_item() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    capture = received(pipeline, FORCED_QUESTION)

    # Execute
    pipeline.process(capture)

    # Assert
    assert store.list_items() == []


def test_a_link_containing_a_question_mark_is_classified_like_any_other_message() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)

    # Execute
    result = pipeline.handle(a_message(LINK_WITH_A_QUERY))

    # Assert
    assert (type(result), len(filer.calls)) == (Filed, 1)


def test_a_pending_question_mark_text_is_a_request_on_retry_without_the_ai() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = received(pipeline, FORCED_QUESTION)

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert (results, filer.calls) == ([IsRequest(capture.with_status(CaptureStatus.REQUEST))], [])


def test_a_retried_request_is_no_longer_pending() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    received(pipeline, FORCED_QUESTION)
    pipeline.retry_pending()

    # Execute
    pending = store.pending_captures()

    # Assert
    assert pending == []


def test_a_question_mark_capture_whose_item_already_exists_is_resumed_as_filed() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    capture = received(pipeline, FORCED_QUESTION)
    item = an_item(id=capture.item_id, capture_id=capture.id)
    store.save_item(item)

    # Execute
    result = pipeline.process(capture)

    # Assert
    assert result == Filed(item, unsure=False)
