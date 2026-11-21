from datetime import UTC, datetime
from pathlib import Path

from eval_builders import a_named_model, a_target, arm_headings
from eval_files import SHIPPED_CASES
from eval_rig import UTC_ZONE
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr

from stash.config import ProviderName
from stash.evaluation import EvalArm, evaluate, load_cases, render_report

NOON = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
LOCAL_ANSWER = {"route": "capture", "item_type": "place", "title": "Somewhere", "stage": "want_to"}
REFERENCE_ANSWER = {"route": "capture", "item_type": "recipe", "title": "Dinner", "stage": "inbox"}


def an_image_reader(path: Path) -> bytes:
    return b"png bytes"


def compare_two_models_on_the_shipped_cases() -> str:
    targets = [
        a_target(
            ProviderName.OLLAMA, text=a_named_model("local", FakeChatModel(reply=LOCAL_ANSWER))
        ),
        a_target(
            ProviderName.OPENROUTER,
            text=a_named_model("reference", FakeChatModel(reply=REFERENCE_ANSWER)),
        ),
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
    assert (
        "| metric | ollama:local thinking=default | openrouter:reference thinking=default |"
        in report
    )


def test_comparing_two_models_on_every_arm_prints_one_table_per_arm_with_its_case_count() -> None:
    # Execute
    report = compare_two_models_on_the_shipped_cases()

    # Assert
    assert arm_headings(report) == [
        "### text arm (30 cases)",
        "### vision arm (3 cases)",
        "### ocr arm (3 cases)",
    ]
