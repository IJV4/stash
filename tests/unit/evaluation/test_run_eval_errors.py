from pathlib import Path

from eval_builders import a_text_case, an_expectation, an_image_case
from eval_rig import an_answer, run_cases
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr
from fakes.scripted_chat_model import ScriptedChatModel

from stash.domain import ItemType, Stage
from stash.evaluation import EvalArm, EvalField, NoOcr, OcrError
from stash.evaluation.runner import ERROR_LIMIT
from stash.llm import LlmUnavailable

SCORED_EVERYTHING = an_expectation(item_type=ItemType.PLACE, stage=Stage.WANT_TO)


def test_an_unavailable_model_marks_the_case_as_an_error_naming_the_failure() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("ollama is down"))

    # Execute
    result = run_cases([a_text_case()], model).results[0]

    # Assert
    assert result.error == "LlmUnavailable: ollama is down"


def test_an_unavailable_model_fails_every_field_the_case_would_have_scored() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("ollama is down"))
    case = a_text_case(expect=SCORED_EVERYTHING)

    # Execute
    result = run_cases([case], model).results[0]

    # Assert
    assert result.failed_fields == {EvalField.ROUTE, EvalField.ITEM_TYPE, EvalField.STAGE}


def test_an_unavailable_model_passes_no_field() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("ollama is down"))

    # Execute
    result = run_cases([a_text_case(expect=SCORED_EVERYTHING)], model).results[0]

    # Assert
    assert result.passed_fields == frozenset()


def test_an_errored_case_counts_in_the_error_count_of_the_run() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("ollama is down"))

    # Execute
    run = run_cases([a_text_case()], model)

    # Assert
    assert run.error_count(EvalArm.TEXT) == 1


def test_the_run_continues_with_the_next_case_after_an_error() -> None:
    # Setup
    model = ScriptedChatModel([LlmUnavailable("blip"), an_answer()])
    cases = [a_text_case(id="a"), a_text_case(id="b")]

    # Execute
    run = run_cases(cases, model)

    # Assert
    assert [result.error is None for result in run.results] == [False, True]


def test_a_long_error_message_is_clipped() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("x" * 5000))

    # Execute
    result = run_cases([a_text_case()], model).results[0]

    # Assert
    assert result.error is not None and len(result.error) <= ERROR_LIMIT


def test_an_error_message_is_collapsed_onto_one_line() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("first\nsecond"))

    # Execute
    result = run_cases([a_text_case()], model).results[0]

    # Assert
    assert result.error == "LlmUnavailable: first second"


def test_a_failing_ocr_marks_the_case_as_an_error() -> None:
    # Setup
    ocr = FakeOcr(error=OcrError("tesseract crashed"))

    # Execute
    result = run_cases([an_image_case()], ocr=ocr, arms=(EvalArm.OCR,)).results[0]

    # Assert
    assert result.error == "OcrError: tesseract crashed"


def test_a_failing_ocr_fails_every_scored_field_without_asking_the_model() -> None:
    # Setup
    model = FakeChatModel(an_answer())
    case = an_image_case(expect=SCORED_EVERYTHING)

    # Execute
    run = run_cases([case], model, ocr=NoOcr(), arms=(EvalArm.OCR,))

    # Assert
    assert (run.results[0].failed_fields, model.calls) == (SCORED_EVERYTHING.scored_fields(), [])


def test_an_unreadable_image_marks_the_vision_case_as_an_error() -> None:
    # Setup
    def unreadable(path: object) -> bytes:
        raise FileNotFoundError("images/recipe_card.png")

    # Execute
    result = run_cases([an_image_case()], arms=(EvalArm.VISION,), read_image=unreadable).results[0]

    # Assert
    assert result.error == "FileNotFoundError: images/recipe_card.png"


def test_a_failure_with_a_blank_message_is_described_by_its_type_name_alone() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable(""))

    # Execute
    result = run_cases([a_text_case()], model).results[0]

    # Assert
    assert result.error == "LlmUnavailable"


def refusing_nul_bytes(path: Path) -> bytes:
    if "\0" in str(path):
        raise ValueError("embedded null byte")
    return b"image"


def test_an_image_name_with_a_nul_byte_marks_the_vision_case_as_an_error() -> None:
    # Setup
    case = an_image_case(image_path=Path("images/card\0.png"))

    # Execute
    result = run_cases([case], arms=(EvalArm.VISION,), read_image=refusing_nul_bytes).results[0]

    # Assert
    assert result.error == "ValueError: embedded null byte"


def test_the_run_continues_with_the_next_case_after_an_image_name_with_a_nul_byte() -> None:
    # Setup
    cases = [
        an_image_case(id="bad", image_path=Path("images/card\0.png")),
        an_image_case(id="good"),
    ]

    # Execute
    run = run_cases(cases, arms=(EvalArm.VISION,), read_image=refusing_nul_bytes)

    # Assert
    assert [result.error is None for result in run.results] == [False, True]
