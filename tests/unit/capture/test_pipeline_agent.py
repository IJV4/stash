import pytest
from builders import a_filing, an_item
from capture_builders import (
    FORCED_QUESTION,
    SAMPLE_TEXT,
    a_pipeline,
    an_agent_message,
    received,
)
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore

from stash.capture import Deferred, Filed
from stash.domain import CaptureStatus, Route
from stash.llm import LlmDeferred, LlmUnavailable


def test_an_agent_capture_starting_with_a_question_mark_is_classified_by_the_ai() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(an_agent_message(FORCED_QUESTION))

    # Assert
    assert [text for text, _ in filer.calls] == [FORCED_QUESTION]


def test_an_agent_capture_starting_with_a_question_mark_is_filed_as_an_item() -> None:
    # Setup
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(an_agent_message(FORCED_QUESTION))

    # Assert
    assert isinstance(result, Filed)


def test_an_agent_capture_starting_with_a_question_mark_ends_up_filed() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    capture = pipeline.receive(an_agent_message(FORCED_QUESTION))
    assert capture is not None

    # Execute
    pipeline.process(capture)

    # Assert
    stored = store.get_capture(capture.id)
    assert stored is not None and stored.status is CaptureStatus.FILED


def test_an_agent_capture_the_ai_answers_with_a_request_is_filed_as_an_unsure_item() -> None:
    # Setup
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)

    # Execute
    result = pipeline.handle(an_agent_message(SAMPLE_TEXT))

    # Assert
    assert isinstance(result, Filed) and result.unsure is True


def test_an_agent_capture_the_ai_answers_with_a_request_saves_an_item() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(an_agent_message(SAMPLE_TEXT))

    # Assert
    assert len(store.list_items()) == 1


def test_a_pending_agent_capture_the_ai_answers_with_a_request_is_filed_on_retry() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    pipeline.receive(an_agent_message(SAMPLE_TEXT))

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [type(result) for result in results] == [Filed]


def test_processing_an_agent_capture_files_a_request_answer_as_an_unsure_item() -> None:
    # Setup
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = pipeline.receive(an_agent_message(SAMPLE_TEXT))
    assert capture is not None

    # Execute
    result = pipeline.process_agent(capture)

    # Assert
    assert isinstance(result, Filed) and result.unsure is True


def test_processing_an_agent_capture_whose_ai_is_unavailable_defers_it() -> None:
    # Setup
    filer = FakeCaptureFiler(error=LlmUnavailable("down"))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = pipeline.receive(an_agent_message(SAMPLE_TEXT))
    assert capture is not None

    # Execute
    result = pipeline.process_agent(capture)

    # Assert
    assert result == Deferred(capture, "ai_unavailable")


def test_processing_an_agent_capture_whose_gpu_is_busy_defers_it() -> None:
    # Setup
    filer = FakeCaptureFiler(error=LlmDeferred("busy"))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = pipeline.receive(an_agent_message(SAMPLE_TEXT))
    assert capture is not None

    # Execute
    result = pipeline.process_agent(capture)

    # Assert
    assert result == Deferred(capture, "gpu_busy")


def test_processing_an_agent_capture_whose_item_already_exists_resumes_it_as_filed() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    capture = pipeline.receive(an_agent_message(SAMPLE_TEXT))
    assert capture is not None
    item = an_item(id=capture.item_id, capture_id=capture.id)
    store.save_item(item)

    # Execute
    result = pipeline.process_agent(capture)

    # Assert
    assert result == Filed(item, unsure=False)


def test_processing_a_capture_from_telegram_as_an_agent_capture_is_refused() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    capture = received(pipeline, SAMPLE_TEXT)

    # Execute / Assert
    with pytest.raises(ValueError, match="agent"):
        pipeline.process_agent(capture)


def test_processing_a_capture_from_telegram_as_an_agent_capture_calls_no_ai() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    capture = received(pipeline, SAMPLE_TEXT)

    # Execute
    with pytest.raises(ValueError, match="agent"):
        pipeline.process_agent(capture)

    # Assert
    assert filer.calls == []
