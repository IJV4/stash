from builders import a_filing
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore
from link_builders import KNIFE_SKILLS_FACTS, VIDEO_URL, a_knife_skills_link

from stash.capture import CapturePipeline, Filed
from stash.enrich.links import LinkInfo

KNIFE_SKILLS = a_knife_skills_link()


def filed_details(pipeline: CapturePipeline, text: str = f"{VIDEO_URL} try this") -> dict[str, str]:
    result = pipeline.handle(a_message(text))
    assert isinstance(result, Filed)
    return dict(result.item.details)


def test_the_item_gets_the_link_title_uploader_and_duration_the_model_left_out() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}),
        FakeCaptureFiler(filing=a_filing(details={})),
    )

    # Execute
    details = filed_details(pipeline)

    # Assert
    assert details == KNIFE_SKILLS_FACTS


def test_the_link_facts_override_what_the_model_wrote_under_the_same_keys() -> None:
    # Setup
    written = {"uploader": "someone else", "duration": "9:99", "link_title": "made up"}
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}),
        FakeCaptureFiler(filing=a_filing(details=written)),
    )

    # Execute
    details = filed_details(pipeline)

    # Assert
    assert details == KNIFE_SKILLS_FACTS


def test_the_link_facts_sit_beside_the_other_details_the_model_wrote() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}),
        FakeCaptureFiler(filing=a_filing(details={"cuisine": "Japanese"})),
    )

    # Execute
    details = filed_details(pipeline)

    # Assert
    assert details["cuisine"] == "Japanese"


def test_the_model_title_is_not_replaced_by_the_link_title() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}),
        FakeCaptureFiler(filing=a_filing(title="Learn knife skills")),
    )

    # Execute
    result = pipeline.handle(a_message(f"{VIDEO_URL} try this"))

    # Assert
    assert isinstance(result, Filed) and result.item.title == "Learn knife skills"


def test_a_link_nothing_is_known_about_leaves_the_details_as_the_model_wrote_them() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: LinkInfo.unknown(VIDEO_URL)}),
        FakeCaptureFiler(filing=a_filing(details={"uploader": "Test Kitchen"})),
    )

    # Execute
    details = filed_details(pipeline)

    # Assert
    assert details == {"uploader": "Test Kitchen"}


def test_a_message_without_a_link_leaves_the_details_as_the_model_wrote_them() -> None:
    # Setup
    pipeline = a_pipeline(
        FreshStore(),
        FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}),
        FakeCaptureFiler(filing=a_filing(details={"city": "Tokyo"})),
    )

    # Execute
    details = filed_details(pipeline, "a thought with no link")

    # Assert
    assert details == {"city": "Tokyo"}


def test_the_item_saved_in_the_store_carries_the_link_facts() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector({VIDEO_URL: KNIFE_SKILLS}), FakeCaptureFiler())

    # Execute
    result = pipeline.handle(a_message(f"{VIDEO_URL} try this"))

    # Assert
    assert isinstance(result, Filed)
    saved = store.get_item(result.item.capture_id)
    assert saved is not None and dict(saved.details) == KNIFE_SKILLS_FACTS
