from datetime import date

import pytest

from stash.filing.prompt import build_messages
from stash.llm import TextPart

TODAY = date(2026, 11, 2)


def system_text() -> str:
    part = build_messages("Ramen", None, TODAY)[0].parts[0]
    assert isinstance(part, TextPart)
    return part.text


@pytest.mark.parametrize("tag", ["<captured>", "<link>"])
def test_the_system_message_names_the_delimiters_that_wrap_untrusted_text(tag: str) -> None:
    # Assert
    assert tag in system_text()
