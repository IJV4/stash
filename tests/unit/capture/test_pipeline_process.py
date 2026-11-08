import pytest
from builders import BASE, LATER, a_filing
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore
from link_builders import a_link_info

from stash.capture import Filed, IsRequest
from stash.domain import CaptureStatus, Item, Route

FIRST_URL = "https://example.com/first"
SECOND_URL = "https://example.com/second"


def test_a_message_with_a_link_inspects_only_the_first_link() -> None:
    # Setup
    inspector = FakeLinkInspector()
    pipeline = a_pipeline(FreshStore(), inspector, FakeCaptureFiler())

    # Execute
    pipeline.handle(a_message(f"{FIRST_URL} and {SECOND_URL}"))

    # Assert
    assert inspector.inspected == [FIRST_URL]


def test_a_message_without_a_link_inspects_nothing() -> None:
    # Setup
    inspector = FakeLinkInspector()
    pipeline = a_pipeline(FreshStore(), inspector, FakeCaptureFiler())

    # Execute
    pipeline.handle(a_message("just a thought"))

    # Assert
    assert inspector.inspected == []


def test_the_filer_receives_the_whole_text_and_the_inspected_link() -> None:
    # Setup
    info = a_link_info(url=FIRST_URL, platform="web")
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector({FIRST_URL: info}), filer)
    text = f"{FIRST_URL} try this"

    # Execute
    pipeline.handle(a_message(text))

    # Assert
    assert filer.calls == [(text, info)]


def test_the_filer_receives_no_link_for_a_message_without_one() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(a_message("just a thought"))

    # Assert
    assert filer.calls == [("just a thought", None)]


def test_the_item_is_the_filing_with_the_first_link_as_source_and_the_clock_as_time() -> None:
    # Setup
    filing = a_filing()
    store = FreshStore()
    pipeline = a_pipeline(
        store, FakeLinkInspector(), FakeCaptureFiler(filing=filing), clock=lambda: LATER
    )
    text = f"{FIRST_URL} {SECOND_URL}"

    # Execute
    result = pipeline.handle(a_message(text))

    # Assert
    assert isinstance(result, Filed)
    capture = store.get_capture(result.item.capture_id)
    assert capture is not None
    assert result.item == Item.from_filing(capture.item_id, capture, filing, FIRST_URL, LATER)


def test_a_message_without_a_link_has_no_source_url() -> None:
    # Setup
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(a_message("just a thought"))

    # Assert
    assert isinstance(result, Filed) and result.item.source_url is None


def test_the_filed_item_is_saved_under_the_id_derived_from_its_capture() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(a_message())

    # Assert
    assert isinstance(result, Filed)
    assert store.get_item(result.item.capture_id) == result.item


def test_filing_marks_the_capture_filed() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(a_message())

    # Assert
    assert isinstance(result, Filed)
    capture = store.get_capture(result.item.capture_id)
    assert capture is not None and capture.status is CaptureStatus.FILED


@pytest.mark.parametrize(
    ("route", "unsure"),
    [(Route.CAPTURE, False), (Route.UNSURE, True)],
)
def test_the_result_is_unsure_only_when_the_filing_route_is_unsure(
    route: Route, unsure: bool
) -> None:
    # Setup
    filer = FakeCaptureFiler(filing=a_filing(route=route))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)

    # Execute
    result = pipeline.handle(a_message())

    # Assert
    assert isinstance(result, Filed) and result.unsure is unsure


def test_a_request_route_returns_the_capture_marked_as_a_request() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    capture = pipeline.receive(a_message("what can I do Saturday?"))
    assert capture is not None

    # Execute
    result = pipeline.process(capture)

    # Assert
    assert result == IsRequest(capture.with_status(CaptureStatus.REQUEST))


def test_a_request_route_stores_the_capture_as_a_request() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    capture = pipeline.receive(a_message("what can I do Saturday?"))
    assert capture is not None

    # Execute
    pipeline.process(capture)

    # Assert
    stored = store.get_capture(capture.id)
    assert stored is not None and stored.status is CaptureStatus.REQUEST


def test_a_request_route_creates_no_item() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(filing=a_filing(route=Route.REQUEST))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(a_message("what can I do Saturday?"))

    # Assert
    assert store.list_items() == []


def test_the_item_is_stamped_with_the_injected_clock_not_the_message_time() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(), FakeLinkInspector(), FakeCaptureFiler(), clock=lambda: LATER
    )

    # Execute
    result = pipeline.handle(a_message(received_at=BASE))

    # Assert
    assert isinstance(result, Filed) and result.item.created_at == LATER
