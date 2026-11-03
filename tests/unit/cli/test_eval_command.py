import io
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr

from stash.cli.eval_command import EvalRequest, run_eval_command
from stash.cli.failure import CommandFailed
from stash.config import ProviderName
from stash.evaluation import EvalArm, EvalTarget

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
LATE_EVENING = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)
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


def write_cases(directory: Path, *cases: Mapping[str, Any]) -> Path:
    path = directory / "cases.jsonl"
    path.write_text("\n".join(json.dumps(case) for case in cases) + "\n")
    (directory / "card.png").write_bytes(b"fake png bytes")
    return path


def two_targets() -> dict[ProviderName, EvalTarget]:
    return {
        ProviderName.OPENROUTER: EvalTarget("cloud", FakeChatModel(ANSWER)),
        ProviderName.OLLAMA: EvalTarget("local", FakeChatModel(ANSWER)),
    }


def request(cases: Path, **overrides: Any) -> EvalRequest:
    fields: dict[str, Any] = {
        "providers": None,
        "arms": (EvalArm.TEXT,),
        "cases": cases,
        "out": None,
    }
    return EvalRequest(**{**fields, **overrides})


def evaluated(
    asked: EvalRequest,
    targets: Mapping[ProviderName, EvalTarget] | None = None,
    ocr: FakeOcr | None = None,
    clock_now: datetime = LATE_EVENING,
) -> tuple[int, str]:
    out = io.StringIO()
    exit_code = run_eval_command(
        asked,
        two_targets() if targets is None else targets,
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
    assert header(output) == "| metric | local | cloud |"


def test_eval_compares_the_chosen_providers_in_the_order_given(tmp_path: Path) -> None:
    # Execute
    _, output = evaluated(
        request(write_cases(tmp_path, TEXT_CASE), providers=("openrouter", "ollama"))
    )

    # Assert
    assert header(output) == "| metric | cloud | local |"


def test_eval_compares_a_single_chosen_provider(tmp_path: Path) -> None:
    # Execute
    _, output = evaluated(request(write_cases(tmp_path, TEXT_CASE), providers=("ollama",)))

    # Assert
    assert header(output) == "| metric | local |"


def test_eval_compares_a_provider_named_twice_once(tmp_path: Path) -> None:
    # Execute
    _, output = evaluated(request(write_cases(tmp_path, TEXT_CASE), providers=("ollama", "ollama")))

    # Assert
    assert header(output) == "| metric | local |"


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
    assert [line for line in output.splitlines() if line.startswith("###")] == [
        "### ocr arm (1 cases)"
    ]


def test_eval_reads_images_with_the_given_ocr(tmp_path: Path) -> None:
    # Setup
    ocr = FakeOcr("Lemon chicken")

    # Execute
    evaluated(
        request(write_cases(tmp_path, IMAGE_CASE), providers=("ollama",), arms=(EvalArm.OCR,)),
        ocr=ocr,
    )

    # Assert
    assert ocr.paths == [tmp_path / "card.png"]


def test_eval_fills_in_todays_date_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    model = FakeChatModel(ANSWER)
    targets = {ProviderName.OLLAMA: EvalTarget("local", model)}

    # Execute
    evaluated(request(write_cases(tmp_path, TEXT_CASE)), targets)

    # Assert
    sent = " ".join(part.text for part in model.calls[0][-1].parts if hasattr(part, "text"))
    assert "2026-11-02" in sent


def test_eval_with_a_provider_that_is_not_configured_fails_with_exit_code_2(
    tmp_path: Path,
) -> None:
    # Execute
    with pytest.raises(CommandFailed) as failure:
        evaluated(request(write_cases(tmp_path, TEXT_CASE), providers=("ollama", "groq")))

    # Assert
    assert (failure.value.exit_code, str(failure.value)) == (2, "provider groq is not configured")


def test_eval_with_a_known_provider_that_has_no_settings_says_it_is_not_configured(
    tmp_path: Path,
) -> None:
    # Setup
    targets = {ProviderName.OLLAMA: EvalTarget("local", FakeChatModel(ANSWER))}

    # Execute
    with pytest.raises(CommandFailed) as failure:
        evaluated(request(write_cases(tmp_path, TEXT_CASE), providers=("openrouter",)), targets)

    # Assert
    assert str(failure.value) == "provider openrouter is not configured"


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


def refused_out(asked: EvalRequest, targets: Mapping[ProviderName, EvalTarget]) -> CommandFailed:
    with pytest.raises(CommandFailed) as failure:
        evaluated(asked, targets)
    return failure.value


def test_eval_with_an_out_path_that_is_the_cases_file_fails_with_exit_code_2(
    tmp_path: Path,
) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    failure = refused_out(request(cases, out=cases), two_targets())

    # Assert
    assert failure.exit_code == 2


def test_eval_with_an_out_path_that_is_the_cases_file_leaves_the_cases_untouched(
    tmp_path: Path,
) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)
    original = cases.read_text()

    # Execute
    refused_out(request(cases, out=cases), two_targets())

    # Assert
    assert cases.read_text() == original


def test_eval_with_an_out_path_that_is_the_cases_file_asks_no_model(tmp_path: Path) -> None:
    # Setup
    model = FakeChatModel(ANSWER)
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    refused_out(request(cases, out=cases), {ProviderName.OLLAMA: EvalTarget("local", model)})

    # Assert
    assert model.calls == []


def test_eval_refuses_an_out_path_that_reaches_the_cases_file_by_another_spelling(
    tmp_path: Path,
) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)
    (tmp_path / "reports").mkdir()
    roundabout = tmp_path / "reports" / ".." / "cases.jsonl"

    # Execute
    failure = refused_out(request(cases, out=roundabout), two_targets())

    # Assert
    assert str(failure) == f"--out {roundabout} is the cases file"


@pytest.mark.parametrize(
    "name",
    ["notes.jsonl", "notes.json", "card.png", "card.jpg", "card.jpeg", "card.webp", "card.gif"],
)
def test_eval_refuses_an_out_path_with_a_cases_or_image_suffix(tmp_path: Path, name: str) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    failure = refused_out(request(cases, out=tmp_path / name), two_targets())

    # Assert
    assert (failure.exit_code, str(failure)) == (
        2,
        f"--out {tmp_path / name} would overwrite a cases or image file",
    )


def test_eval_refuses_an_out_path_suffix_whatever_its_case(tmp_path: Path) -> None:
    # Setup
    cases = write_cases(tmp_path, TEXT_CASE)

    # Execute
    failure = refused_out(request(cases, out=tmp_path / "CARD.PNG"), two_targets())

    # Assert
    assert failure.exit_code == 2


def test_eval_with_a_refused_out_path_asks_no_model_and_creates_no_file(tmp_path: Path) -> None:
    # Setup
    model = FakeChatModel(ANSWER)
    cases = write_cases(tmp_path, TEXT_CASE)
    refused = tmp_path / "card.gif"

    # Execute
    refused_out(request(cases, out=refused), {ProviderName.OLLAMA: EvalTarget("local", model)})

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


def test_eval_refuses_an_out_path_that_is_a_cases_file_with_an_unusual_suffix(
    tmp_path: Path,
) -> None:
    # Setup
    cases = tmp_path / "cases.txt"
    cases.write_text(json.dumps(TEXT_CASE) + "\n")

    # Execute
    failure = refused_out(request(cases, out=cases), two_targets())

    # Assert
    assert str(failure) == f"--out {cases} is the cases file"
