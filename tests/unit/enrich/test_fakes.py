from fakes.link_inspector import FakeLinkInspector
from link_builders import VIDEO_URL, a_link_info

from stash.enrich.links import LinkInfo


def test_a_fake_link_inspector_returns_the_info_configured_for_the_url() -> None:
    # Setup
    info = a_link_info()
    inspector = FakeLinkInspector({VIDEO_URL: info})

    # Execute
    result = inspector.inspect(VIDEO_URL)

    # Assert
    assert result == info


def test_a_fake_link_inspector_returns_unknown_for_an_unconfigured_url() -> None:
    # Execute
    result = FakeLinkInspector().inspect("https://example.com/a")

    # Assert
    assert result == LinkInfo.unknown("https://example.com/a")


def test_a_fake_link_inspector_records_each_url_it_was_asked_about() -> None:
    # Setup
    inspector = FakeLinkInspector()

    # Execute
    inspector.inspect("https://a.com/1")
    inspector.inspect("https://b.com/2")

    # Assert
    assert inspector.inspected == ["https://a.com/1", "https://b.com/2"]
