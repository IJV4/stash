import pytest
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from filing_rig import build_filer
from link_builders import a_link_info

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


def test_no_text_and_no_link_is_titled_untitled() -> None:
    # Assert
    assert build_filer(FakeChatModel()).file("", None).title == "Untitled"


def test_no_text_and_no_link_does_not_call_the_model() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    build_filer(model).file("  ", None)

    # Assert
    assert model.calls == []


def test_no_text_and_no_link_is_filed_even_when_the_gpu_is_busy() -> None:
    # Setup
    filer = build_filer(FakeChatModel(), busy=FakeBusy(busy=True))

    # Execute
    filing = filer.file("", None)

    # Assert
    assert filing.route is Route.CAPTURE


def test_a_link_without_text_is_still_sent_to_the_ai() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    build_filer(model).file("", a_link_info())

    # Assert
    assert len(model.calls) == 1
