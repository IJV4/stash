from builders import an_item
from capture_builders import (
    FORCED_QUESTION,
    a_pipeline,
    received,
)
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore

from stash.capture import Filed


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
