from datetime import UTC, datetime
from pathlib import Path

from eval_files import SHIPPED_CASES
from eval_rig import UTC_ZONE
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr

from stash.evaluation import EvalArm, EvalTarget, evaluate, load_cases, render_report

NOON = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
LOCAL_ANSWER = {"route": "capture", "item_type": "place", "title": "Somewhere", "stage": "want_to"}
REFERENCE_ANSWER = {"route": "capture", "item_type": "recipe", "title": "Dinner", "stage": "inbox"}


def an_image_reader(path: Path) -> bytes:
    return b"png bytes"


def compare_two_models_on_the_shipped_cases() -> str:
    targets = [
        EvalTarget("local", FakeChatModel(reply=LOCAL_ANSWER)),
        EvalTarget("reference", FakeChatModel(reply=REFERENCE_ANSWER)),
    ]
    runs = evaluate(
        load_cases(SHIPPED_CASES),
        targets,
        list(EvalArm),
        FakeOcr("Lemon Garlic Roast Chicken"),
        lambda: NOON,
        read_image=an_image_reader,
        timezone=UTC_ZONE,
    )
    return render_report(runs)


def test_comparing_two_models_prints_a_column_for_each_model_label() -> None:
    # Execute
    report = compare_two_models_on_the_shipped_cases()

    # Assert
    assert "| metric | local | reference |" in report


def test_comparing_two_models_on_every_arm_prints_one_table_per_arm_with_its_case_count() -> None:
    # Execute
    report = compare_two_models_on_the_shipped_cases()

    # Assert
    headings = [line for line in report.splitlines() if line.startswith("### ")]
    assert headings == [
        "### text arm (22 cases)",
        "### vision arm (3 cases)",
        "### ocr arm (3 cases)",
    ]
