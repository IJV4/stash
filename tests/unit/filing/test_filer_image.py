import pytest
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from filing_rig import build_filer

from stash.domain import ItemType, Route
from stash.filing import inbox_filing
from stash.llm import ImagePart, LlmBadOutput, LlmUnavailable, TextPart

IMAGE = ImagePart("data:image/png;base64,AAAA")


def test_the_image_is_sent_after_the_text_part_of_the_user_message() -> None:
    # Setup
    vision = FakeChatModel()

    # Execute
    build_filer(FakeChatModel()).file_image(IMAGE, "Recipe card", vision)

    # Assert
    assert vision.calls[0][1].parts[1:] == (IMAGE,)


def test_the_note_is_the_captured_text() -> None:
    # Setup
    vision = FakeChatModel()

    # Execute
    build_filer(FakeChatModel()).file_image(IMAGE, "Recipe card", vision)

    # Assert
    part = vision.calls[0][1].parts[0]
    assert isinstance(part, TextPart) and "<captured>\nRecipe card\n</captured>" in part.text


def test_the_supplied_model_is_used_instead_of_the_routed_one() -> None:
    # Setup
    routed, supplied = FakeChatModel(), FakeChatModel()

    # Execute
    build_filer(routed).file_image(IMAGE, "Recipe card", supplied)

    # Assert
    assert (len(routed.calls), len(supplied.calls)) == (0, 1)


def test_a_busy_gpu_does_not_stop_a_model_the_caller_chose() -> None:
    # Setup
    filer = build_filer(FakeChatModel(), busy=FakeBusy(busy=True))

    # Execute
    filing = filer.file_image(IMAGE, "Recipe card", FakeChatModel(reply={"item_type": "recipe"}))

    # Assert
    assert filing.item_type is ItemType.RECIPE


def test_an_image_filing_is_parsed_with_the_note_as_the_title_fallback() -> None:
    # Setup
    filer = build_filer(FakeChatModel())

    # Execute
    filing = filer.file_image(IMAGE, "Recipe card", FakeChatModel())

    # Assert
    assert filing.title == "Recipe card"


def test_an_image_answer_that_is_not_json_files_an_unsure_inbox_capture() -> None:
    # Setup
    filer = build_filer(FakeChatModel())

    # Execute
    filing = filer.file_image(IMAGE, "Recipe card", FakeChatModel(error=LlmBadOutput("no")))

    # Assert
    assert filing == inbox_filing("Recipe card", Route.UNSURE)


def test_an_unavailable_vision_model_propagates() -> None:
    # Setup
    filer = build_filer(FakeChatModel())

    # Execute / Assert
    with pytest.raises(LlmUnavailable):
        filer.file_image(IMAGE, "Recipe card", FakeChatModel(error=LlmUnavailable("down")))


def test_today_in_an_image_filing_is_the_owners_local_date() -> None:
    # Setup
    vision = FakeChatModel()

    # Execute
    build_filer(FakeChatModel()).file_image(IMAGE, "Recipe card", vision)

    # Assert
    part = vision.calls[0][1].parts[0]
    assert isinstance(part, TextPart) and part.text.startswith("Today is Monday 2026-11-02.")
