from datetime import date

from stash.enrich.links import LinkInfo
from stash.filing.prompt import CAPTURED_TEXT_LIMIT, build_messages
from stash.llm import TextPart

TODAY = date(2026, 11, 2)
LINK_BLOCK = (
    "<link>\n"
    "url: https://www.youtube.com/watch?v=abc123\n"
    "platform: youtube\n"
    "title: Ramen crawl\n"
    "description: Five bowls in one night\n"
    "uploader: Hana Eats\n"
    "duration_seconds: 61\n"
    "captions: yes\n"
    "</link>"
)


def user_text(text: str, link: LinkInfo | None = None, today: date = TODAY) -> str:
    part = build_messages(text, link, today)[1].parts[0]
    assert isinstance(part, TextPart)
    return part.text


def test_the_captured_text_limit_is_4000_characters() -> None:
    # Assert
    assert CAPTURED_TEXT_LIMIT == 4000
