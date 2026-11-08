from capture_builders import RAMEN_URL, a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.hung_link_inspector import HungLinkInspector
from fakes.store_factories import FreshStore

from stash.capture import Filed
from stash.enrich.deadline import DeadlineInspector
from stash.enrich.links import LinkInfo

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
SHORT_DEADLINE_SECONDS = 0.005


def test_a_link_that_takes_too_long_to_inspect_is_filed_from_the_owners_own_words() -> None:
    # Setup
    hung = HungLinkInspector()
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), DeadlineInspector(hung, SHORT_DEADLINE_SECONDS), filer)

    # Execute
    result = pipeline.handle(a_message(f"{RAMEN_URL} try this in March"))
    hung.release.set()

    # Assert
    assert isinstance(result, Filed)
    assert filer.calls == [(f"{RAMEN_URL} try this in March", LinkInfo.unknown(RAMEN_URL))]
