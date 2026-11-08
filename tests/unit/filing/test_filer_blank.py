import pytest
from fakes.chat_model import FakeChatModel
from filing_rig import build_filer

from stash.domain import ItemType, Route, Stage


@pytest.mark.parametrize("text", ["", "  \n\t "])
def test_no_text_and_no_link_is_filed_as_an_other_inbox_capture(text: str) -> None:
    # Setup
    filer = build_filer(FakeChatModel(reply={"item_type": "place", "route": "request"}))

    # Execute
    filing = filer.file(text, None)

    # Assert
    assert (filing.route, filing.item_type, filing.stage) == (
        Route.CAPTURE,
        ItemType.OTHER,
        Stage.INBOX,
    )


def test_no_text_and_no_link_does_not_call_the_model() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    build_filer(model).file("  ", None)

    # Assert
    assert model.calls == []
