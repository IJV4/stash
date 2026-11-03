import base64
from pathlib import Path

from eval_builders import a_text_case, an_expectation, an_image_case
from eval_rig import IMAGE_BYTES, an_answer, run_cases
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr
from filing_rig import sent_texts

from stash.domain import ItemType
from stash.evaluation import EvalArm, EvalField
from stash.llm import ImagePart

RECIPE_CARD = Path("images/recipe_card.png")
IMAGE_URL = f"data:image/png;base64,{base64.b64encode(IMAGE_BYTES).decode('ascii')}"


def test_the_vision_arm_sends_the_image_to_the_model_as_a_data_url() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases([an_image_case(image_path=RECIPE_CARD)], model, arms=(EvalArm.VISION,))

    # Assert
    assert model.calls[0][1].parts[1:] == (ImagePart(IMAGE_URL),)


def test_the_vision_arm_sends_the_note_with_the_image() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases([an_image_case(text="save this one")], model, arms=(EvalArm.VISION,))

    # Assert
    assert "<captured>\nsave this one\n</captured>" in sent_texts(model)[1]


def test_the_vision_arm_uses_the_vision_model_of_the_target() -> None:
    # Setup
    text_model, vision_model = FakeChatModel(an_answer()), FakeChatModel(an_answer())

    # Execute
    run_cases([an_image_case()], text_model, arms=(EvalArm.VISION,), vision_model=vision_model)

    # Assert
    assert (len(text_model.calls), len(vision_model.calls)) == (0, 1)


def test_the_vision_arm_falls_back_to_the_text_model_when_the_target_has_no_vision_model() -> None:
    # Setup
    text_model = FakeChatModel(an_answer())

    # Execute
    run_cases([an_image_case()], text_model, arms=(EvalArm.VISION,))

    # Assert
    assert len(text_model.calls) == 1


def test_the_vision_arm_judges_the_filing_against_the_expectation() -> None:
    # Setup
    case = an_image_case(expect=an_expectation(item_type=ItemType.RECIPE))
    model = FakeChatModel(an_answer(item_type="recipe"))

    # Execute
    result = run_cases([case], model, arms=(EvalArm.VISION,)).results[0]

    # Assert
    assert (result.arm, EvalField.ITEM_TYPE in result.passed_fields) == (EvalArm.VISION, True)


def test_the_vision_arm_skips_text_cases() -> None:
    # Execute
    run = run_cases([a_text_case()], arms=(EvalArm.VISION,))

    # Assert
    assert run.results == ()


def test_the_ocr_arm_reads_the_image_of_the_case() -> None:
    # Setup
    ocr = FakeOcr("Lemon Garlic Roast Chicken")

    # Execute
    run_cases([an_image_case(image_path=RECIPE_CARD)], ocr=ocr, arms=(EvalArm.OCR,))

    # Assert
    assert ocr.paths == [RECIPE_CARD]


def test_the_ocr_arm_files_the_text_the_ocr_read() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases(
        [an_image_case(text="")],
        model,
        ocr=FakeOcr("Lemon Garlic Roast Chicken"),
        arms=(EvalArm.OCR,),
    )

    # Assert
    assert "<captured>\nLemon Garlic Roast Chicken\n</captured>" in sent_texts(model)[1]


def test_the_ocr_arm_files_the_note_followed_by_the_text_the_ocr_read() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases(
        [an_image_case(text="save this")],
        model,
        ocr=FakeOcr("Lemon Garlic Roast Chicken"),
        arms=(EvalArm.OCR,),
    )

    # Assert
    assert "<captured>\nsave this\nLemon Garlic Roast Chicken\n</captured>" in sent_texts(model)[1]


def test_the_ocr_arm_sends_no_image_to_the_model() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases([an_image_case()], model, ocr=FakeOcr("Lemon"), arms=(EvalArm.OCR,))

    # Assert
    assert len(model.calls[0][1].parts) == 1


def test_the_ocr_arm_skips_text_cases() -> None:
    # Setup
    ocr = FakeOcr("anything")

    # Execute
    run = run_cases([a_text_case()], ocr=ocr, arms=(EvalArm.OCR,))

    # Assert
    assert (run.results, ocr.paths) == ((), [])


def test_each_selected_arm_runs_the_cases_it_applies_to_in_the_order_given() -> None:
    # Setup
    cases = [a_text_case(id="t"), an_image_case(id="i")]

    # Execute
    run = run_cases(cases, arms=(EvalArm.VISION, EvalArm.OCR, EvalArm.TEXT))

    # Assert
    assert [(result.arm, result.case_id) for result in run.results] == [
        (EvalArm.VISION, "i"),
        (EvalArm.OCR, "i"),
        (EvalArm.TEXT, "t"),
    ]
