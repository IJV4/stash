from builders import BASE, a_source
from capture_builders import INDENTED_FORCED_QUESTION, a_message, a_pipeline, received
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore

from stash.capture import Duplicate, Filed
from stash.domain import CaptureStatus, RawCapture


def test_receive_stores_a_pending_capture_built_from_the_message() -> None:
    # Setup
    store = MemoryStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    message = a_message("Ramen", media_paths=("media/a.jpg",))

    # Execute
    pipeline.receive(message)

    # Assert
    assert store.pending_captures() == [
        RawCapture(
            id=f"{1:032x}",
            source=a_source(),
            received_at=BASE,
            text="Ramen",
            media_paths=("media/a.jpg",),
            status=CaptureStatus.PENDING,
        )
    ]


def test_receive_returns_the_capture_it_stored() -> None:
    # Setup
    store = MemoryStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    capture = pipeline.receive(a_message())

    # Assert
    assert [capture] == store.pending_captures()


def test_receive_returns_none_for_a_message_already_received() -> None:
    # Setup
    pipeline = a_pipeline(MemoryStore(), FakeLinkInspector(), FakeCaptureFiler())
    pipeline.receive(a_message(message_id="m1"))

    # Execute
    second = pipeline.receive(a_message(message_id="m1", text="again"))

    # Assert
    assert second is None


def test_receive_of_a_duplicate_leaves_the_stored_capture_unchanged() -> None:
    # Setup
    store = MemoryStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    first = pipeline.receive(a_message(message_id="m1", text="first"))

    # Execute
    pipeline.receive(a_message(message_id="m1", text="again"))

    # Assert
    assert store.pending_captures() == [first]


def test_receive_gives_different_messages_different_capture_ids() -> None:
    # Setup
    store = MemoryStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    pipeline.receive(a_message(message_id="m1"))
    pipeline.receive(a_message(message_id="m2"))

    # Assert
    assert len({capture.id for capture in store.pending_captures()}) == 2


def test_handle_receives_then_processes_the_message() -> None:
    # Setup
    store = MemoryStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(a_message("Ramen"))

    # Assert
    assert isinstance(result, Filed) and store.get_item(result.item.id) == result.item


def test_handle_of_a_duplicate_message_returns_duplicate() -> None:
    # Setup
    pipeline = a_pipeline(MemoryStore(), FakeLinkInspector(), FakeCaptureFiler())
    pipeline.handle(a_message())

    # Execute
    result = pipeline.handle(a_message())

    # Assert
    assert result == Duplicate()


def test_handle_of_a_duplicate_message_does_not_ask_the_filer_again() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(MemoryStore(), FakeLinkInspector(), filer)
    pipeline.handle(a_message())

    # Execute
    pipeline.handle(a_message())

    # Assert
    assert len(filer.calls) == 1


def test_receive_keeps_the_message_text_unchanged_including_a_leading_question_mark() -> None:
    # Setup
    pipeline = a_pipeline(MemoryStore(), FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    capture = received(pipeline, INDENTED_FORCED_QUESTION)

    # Assert
    assert capture.text == INDENTED_FORCED_QUESTION
