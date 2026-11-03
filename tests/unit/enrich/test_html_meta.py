from html_rig import build_html_rig, html_page

from stash.enrich.links import LinkInfo

PAGE_URL = "https://example.com/ramen"
OG_PAGE = (
    "<html><head><title>Plain title</title>"
    '<meta name="description" content="Plain description">'
    '<meta property="og:title" content="Ramen Tokyo">'
    '<meta property="og:description" content="Best bowls in Shibuya">'
    "</head><body>hello</body></html>"
)


def inspect_page(body: str, url: str = PAGE_URL) -> LinkInfo:
    return build_html_rig(lambda request: html_page(body)).inspector.inspect(url)


def test_open_graph_tags_describe_the_page() -> None:
    # Execute / Assert
    assert inspect_page(OG_PAGE) == LinkInfo(
        url=PAGE_URL,
        platform="web",
        title="Ramen Tokyo",
        description="Best bowls in Shibuya",
        uploader=None,
        duration_s=None,
        has_captions=False,
    )


def test_the_title_element_stands_in_when_there_is_no_open_graph_title() -> None:
    # Execute / Assert
    assert inspect_page("<title>Plain title</title>").title == "Plain title"


def test_the_meta_description_stands_in_when_there_is_no_open_graph_description() -> None:
    # Execute
    info = inspect_page('<meta name="description" content="Plain description">')

    # Assert
    assert info.description == "Plain description"


def test_a_page_without_a_description_has_none() -> None:
    # Execute / Assert
    assert inspect_page("<title>Plain title</title>").description is None


def test_a_blank_open_graph_title_falls_back_to_the_title_element() -> None:
    # Execute
    info = inspect_page('<title>Real</title><meta property="og:title" content="  ">')

    # Assert
    assert info.title == "Real"


def test_only_the_first_title_element_is_used() -> None:
    # Execute / Assert
    assert inspect_page("<title>First</title><title>Second</title>").title == "First"


def test_tag_and_attribute_names_and_property_values_match_case_insensitively() -> None:
    # Execute
    info = inspect_page('<META PROPERTY="OG:Title" CONTENT="Shouting"><TITLE>x</TITLE>')

    # Assert
    assert info.title == "Shouting"


def test_html_entities_in_the_title_are_decoded() -> None:
    # Execute / Assert
    assert inspect_page("<title>Fish &amp; Chips</title>").title == "Fish & Chips"


def test_a_meta_tag_without_content_is_ignored() -> None:
    # Execute
    info = inspect_page('<meta property="og:title"><title>Fallback</title>')

    # Assert
    assert info.title == "Fallback"


def test_a_page_with_neither_title_nor_description_is_unknown() -> None:
    # Execute / Assert
    assert inspect_page("<p>just text</p>") == LinkInfo.unknown(PAGE_URL)


def test_malformed_markup_without_a_title_is_unknown() -> None:
    # Execute / Assert
    assert inspect_page("<<<>>><!-- <meta <title") == LinkInfo.unknown(PAGE_URL)


def test_the_platform_comes_from_the_original_url() -> None:
    # Execute / Assert
    assert inspect_page(OG_PAGE, "https://www.instagram.com/p/abc").platform == "instagram"


def test_the_first_of_two_open_graph_titles_wins() -> None:
    # Execute
    info = inspect_page(
        '<meta property="og:title" content="First"><meta property="og:title" content="Second">'
    )

    # Assert
    assert info.title == "First"


def test_an_open_graph_title_with_blank_content_does_not_hide_a_later_one() -> None:
    # Execute
    info = inspect_page(
        '<meta property="og:title" content=" "><meta property="og:title" content="Real">'
    )

    # Assert
    assert info.title == "Real"
