from collections.abc import Callable

import pytest
from builders import an_item, an_outcome
from library_html_rig import (
    a_kept_snapshot,
    a_snapshot,
    parsed_markup,
    with_unchecked_source_url,
)

from stash.domain import ItemType, Stage
from stash.library_html import LibraryEntry, LibrarySnapshot, render_library

SCRIPT_PAYLOAD = "<script>alert(1)</script>"
IMAGE_PAYLOAD = '"><img src=x onerror=alert(1)>'
SCRIPT_URL = "javascript:alert(1)"
QUOTED_URL = 'https://example.test/?a="b" onmouseover="alert(1)"&c=<d>'

Placement = Callable[[str], LibrarySnapshot]

PLACEMENTS: dict[str, Placement] = {
    "kept title": lambda text: a_kept_snapshot(an_item(kept=True, title=text)),
    "kept note": lambda text: a_kept_snapshot(an_item(kept=True, note=text)),
    "outcome notes": lambda text: a_kept_snapshot(an_item(), [an_outcome(notes=text)]),
    "takeaway": lambda text: a_kept_snapshot(an_item(), [an_outcome(takeaways=(text,))]),
    "media summary": lambda text: a_snapshot(
        kept={ItemType.MEDIA: [LibraryEntry(an_item(item_type=ItemType.MEDIA), [], text)]}
    ),
    "done title": lambda text: a_snapshot(
        done_by_year={2026: [LibraryEntry(an_item(title=text), [an_outcome()])]}
    ),
    "want to title": lambda text: a_snapshot(want_to={ItemType.PLACE: [an_item(title=text)]}),
    "dropped title": lambda text: a_snapshot(dropped=[an_item(stage=Stage.DROPPED, title=text)]),
    "drop reason": lambda text: a_snapshot(
        dropped=[an_item(stage=Stage.DROPPED, drop_reason=text)]
    ),
}


def page_with(payload: str, placement: str) -> str:
    return render_library(PLACEMENTS[placement](payload))


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_stored_text_holding_a_script_tag_creates_no_script_element(placement: str) -> None:
    # Execute
    page = page_with(SCRIPT_PAYLOAD, placement)

    # Assert
    assert "script" not in parsed_markup(page).tags


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_stored_text_that_closes_a_tag_and_adds_an_image_creates_no_image_element(
    placement: str,
) -> None:
    # Execute
    page = page_with(IMAGE_PAYLOAD, placement)

    # Assert
    assert "img" not in parsed_markup(page).tags


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_stored_text_adding_an_event_handler_creates_no_on_attribute(placement: str) -> None:
    # Execute
    page = page_with(IMAGE_PAYLOAD, placement)

    # Assert
    assert [name for name in parsed_markup(page).attributes if name.startswith("on")] == []


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_stored_text_holding_a_script_tag_is_shown_as_escaped_text(placement: str) -> None:
    # Execute
    page = page_with(SCRIPT_PAYLOAD, placement)

    # Assert
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_stored_text_starting_a_javascript_url_never_contains_the_scheme_literally(
    placement: str,
) -> None:
    # Execute
    page = page_with(SCRIPT_URL.upper(), placement).lower()

    # Assert
    assert "javascript:" not in page


def test_the_page_title_is_escaped() -> None:
    # Execute
    page = render_library(a_snapshot(), title=SCRIPT_PAYLOAD)

    # Assert
    assert "script" not in parsed_markup(page).tags


def test_an_https_source_url_becomes_a_link_that_opens_without_opener_or_referrer() -> None:
    # Setup
    item = an_item(kept=True, source_url="https://example.test/ramen")

    # Execute
    page = render_library(a_kept_snapshot(item))

    # Assert
    assert 'href="https://example.test/ramen" rel="noopener noreferrer"' in page


def test_a_source_url_containing_quotes_cannot_break_out_of_the_href() -> None:
    # Setup
    item = with_unchecked_source_url(an_item(kept=True), QUOTED_URL)

    # Execute
    page = render_library(a_kept_snapshot(item))

    # Assert
    assert "onmouseover" not in parsed_markup(page).attributes


@pytest.mark.parametrize("url", [SCRIPT_URL, "data:text/html,hi", "ftp://example.test/file"])
def test_a_source_url_that_is_not_http_or_https_is_never_made_a_link(url: str) -> None:
    # Setup
    item = with_unchecked_source_url(an_item(kept=True), url)

    # Execute
    page = render_library(a_kept_snapshot(item))

    # Assert
    assert parsed_markup(page).hrefs == []


def test_a_source_url_with_a_script_scheme_is_shown_as_inert_text() -> None:
    # Setup
    item = with_unchecked_source_url(an_item(kept=True), SCRIPT_URL)

    # Execute
    page = render_library(a_kept_snapshot(item))

    # Assert
    assert "javascript&#58;alert(1)" in page
