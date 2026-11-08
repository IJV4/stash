import io
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from eval_builders import an_eval_targets, arm_headings
from eval_files import write_cases
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr

from stash.cli.eval_command import EvalRequest, run_eval_command
from stash.cli.failure import CommandFailed
from stash.config import ProviderName
from stash.evaluation import EvalArm, EvalTargets

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
LATE_EVENING = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)
CLOUD_NAMES = {ProviderName.OPENROUTER: "cloud"}
ANSWER = {"route": "capture", "item_type": "place", "title": "Ramen", "stage": "want_to"}
TEXT_CASE = {
    "id": "t01",
    "arm": "text",
    "text": "Ramen in Shibuya",
    "expect": {"route": "capture"},
}
IMAGE_CASE = {
    "id": "i01",
    "arm": "image",
    "text": "save this",
    "image": "card.png",
    "expect": {"route": "capture"},
}


def request(cases: Path, **overrides: Any) -> EvalRequest:
    fields: dict[str, Any] = {
        "providers": None,
        "thinking": None,
        "arms": (EvalArm.TEXT,),
        "cases": cases,
        "out": None,
    }
    return EvalRequest(**{**fields, **overrides})


def evaluated(
    asked: EvalRequest,
    targets: EvalTargets | None = None,
    ocr: FakeOcr | None = None,
    clock_now: datetime = LATE_EVENING,
) -> tuple[int, str]:
    out = io.StringIO()
    exit_code = run_eval_command(
        asked,
        an_eval_targets(ProviderName.OPENROUTER, ProviderName.OLLAMA, model_names=CLOUD_NAMES)
        if targets is None
        else targets,
        FakeOcr() if ocr is None else ocr,
        lambda: clock_now,
        LOS_ANGELES,
        out,
    )
    return exit_code, out.getvalue()


def header(output: str) -> str:
    return next(line for line in output.splitlines() if line.startswith("| metric"))


def test_eval_without_providers_compares_every_configured_provider_in_provider_order(
    tmp_path: Path,
) -> None:
    # Execute
    _, output = evaluated(request(write_cases(tmp_path, TEXT_CASE)))

    # Assert
    assert (
        header(output)
        == "| metric | ollama:local thinking=default | openrouter:cloud thinking=default |"
    )


def test_eval_exits_0_after_printing_the_report(tmp_path: Path) -> None:
    # Execute
    exit_code, output = evaluated(request(write_cases(tmp_path, TEXT_CASE)))

    # Assert
    assert (exit_code, output.startswith("### text arm (1 cases)")) == (0, True)


def test_eval_runs_only_the_requested_arms(tmp_path: Path) -> None:
    # Execute
    _, output = evaluated(
        request(write_cases(tmp_path, TEXT_CASE, IMAGE_CASE), arms=(EvalArm.OCR,))
    )

    # Assert
    assert arm_headings(output) == ["### ocr arm (1 cases)"]


def test_eval_fills_in_todays_date_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    model = FakeChatModel(ANSWER)
    targets = an_eval_targets(model=model)

    # Execute
    evaluated(request(write_cases(tmp_path, TEXT_CASE)), targets)

    # Assert
    sent = " ".join(part.text for part in model.calls[0][-1].parts if hasattr(part, "text"))
    assert "2026-11-02" in sent


def test_eval_with_a_cases_file_that_is_missing_fails_with_exit_code_2(tmp_path: Path) -> None:
    # Execute
    with pytest.raises(CommandFailed) as failure:
        evaluated(request(tmp_path / "missing.jsonl"))

    # Assert
    assert failure.value.exit_code == 2


def test_eval_with_a_bad_cases_line_names_the_line(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "cases.jsonl"
    path.write_text("not json\n")

    # Execute
    with pytest.raises(CommandFailed) as failure:
        evaluated(request(path))

    # Assert
    assert str(failure.value).startswith("line 1:")


def test_eval_saves_the_printed_report_to_the_out_path_creating_its_directory(
    tmp_path: Path,
) -> None:
    # Setup
    saved = tmp_path / "reports" / "eval.md"

    # Execute
    _, output = evaluated(request(write_cases(tmp_path, TEXT_CASE), out=saved))

    # Assert
    assert saved.read_text() == output


def test_eval_with_an_out_path_that_cannot_be_written_fails_with_exit_code_1(
    tmp_path: Path,
) -> None:
    # Setup
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")

    # Execute
    with pytest.raises(CommandFailed) as failure:
        evaluated(request(write_cases(tmp_path, TEXT_CASE), out=blocker / "eval.md"))

    # Assert
    assert failure.value.exit_code == 1


def refused_out(asked: EvalRequest, targets: EvalTargets | None = None) -> CommandFailed:
    with pytest.raises(CommandFailed) as failure:
        evaluated(asked, targets)
    return failure.value


@pytest.mark.parametrize(
    "name",
    ["notes.jsonl", "notes.json", "card.png", "card.jpg", "card.jpeg", "card.webp", "card.gif"],
)
def test_eval_refuses_an_out_path_with_a_cases_or_image_suffix(tmp_path: Path, name: str) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    failure = refused_out(request(cases, out=tmp_path / name))

    # Assert
    assert (failure.exit_code, str(failure)) == (
        2,
        f"--out {tmp_path / name} would overwrite a cases or image file",
    )


def test_eval_refuses_an_out_path_suffix_whatever_its_case(tmp_path: Path) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    failure = refused_out(request(cases, out=tmp_path / "CARD.PNG"))

    # Assert
    assert failure.exit_code == 2


def test_eval_with_a_refused_out_path_asks_no_model_and_creates_no_file(tmp_path: Path) -> None:
    # Setup
    model = FakeChatModel(ANSWER)
    cases = write_cases(tmp_path, TEXT_CASE)
    refused = tmp_path / "card.gif"

    # Execute
    refused_out(request(cases, out=refused), an_eval_targets(model=model))

    # Assert
    assert (model.calls, refused.exists()) == ([], False)


def test_eval_replaces_an_existing_report_without_rewriting_its_old_file(tmp_path: Path) -> None:
    # Setup
    saved = tmp_path / "eval.md"
    saved.write_text("old report")
    elsewhere = tmp_path / "old-link.md"
    os.link(saved, elsewhere)

    # Execute
    evaluated(request(write_cases(tmp_path, TEXT_CASE), out=saved))

    # Assert
    assert elsewhere.read_text() == "old report"


def test_eval_leaves_no_temporary_file_beside_a_saved_report(tmp_path: Path) -> None:
    # Setup
    saved = tmp_path / "reports" / "eval.md"

    # Execute
    evaluated(request(write_cases(tmp_path, TEXT_CASE), out=saved))

    # Assert
    assert [path.name for path in saved.parent.iterdir()] == ["eval.md"]


def test_eval_leaves_no_temporary_file_when_the_report_cannot_replace_its_target(
    tmp_path: Path,
) -> None:
    # Setup
    target = tmp_path / "reports" / "eval.md"
    target.mkdir(parents=True)

    # Execute
    with pytest.raises(CommandFailed):
        evaluated(request(write_cases(tmp_path, TEXT_CASE), out=target))

    # Assert
    assert list(target.parent.iterdir()) == [target]
