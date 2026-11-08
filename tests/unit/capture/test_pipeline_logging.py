import logging

import pytest
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore
from log_records import recording_logs

from stash.llm import LlmDeferred, LlmError, LlmUnavailable

PIPELINE_LOGGER = "stash.capture.pipeline"
PROVIDER_TEXT = "provider says: key sk-fake-123 rejected"


def deferred_entries(error: LlmError) -> tuple[list[tuple[int, str]], str]:
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler(error=error))
    with recording_logs(PIPELINE_LOGGER) as recorder:
        pipeline.handle(a_message())
    return recorder.entries(), store.pending_captures()[0].id


@pytest.mark.parametrize("error", [LlmUnavailable(PROVIDER_TEXT), LlmError(PROVIDER_TEXT)])
def test_an_unavailable_ai_is_logged_at_warning_with_the_exception_type(error: LlmError) -> None:
    # Execute
    entries, capture_id = deferred_entries(error)

    # Assert
    assert entries == [
        (logging.WARNING, f"capture {capture_id} deferred: ai_unavailable ({type(error).__name__})")
    ]


def test_an_unavailable_ai_log_never_carries_the_provider_message() -> None:
    # Execute
    entries, _ = deferred_entries(LlmUnavailable(PROVIDER_TEXT))

    # Assert
    assert "sk-fake-123" not in " ".join(message for _, message in entries)


def test_a_busy_gpu_is_logged_at_info() -> None:
    # Execute
    entries, capture_id = deferred_entries(LlmDeferred("GPU busy"))

    # Assert
    assert entries == [(logging.INFO, f"capture {capture_id} deferred: gpu_busy")]
