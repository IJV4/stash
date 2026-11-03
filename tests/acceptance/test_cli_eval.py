import json
from pathlib import Path

from cli_rig import CliRig, build_cli_rig

TEXT_CASE = {
    "id": "t01",
    "arm": "text",
    "text": "Ichiran ramen in Fukuoka",
    "link": None,
    "expect": {"route": "capture", "item_type": "place"},
}
IMAGE_CASE = {
    "id": "i01",
    "arm": "image",
    "text": "save this",
    "image": "images/card.png",
    "expect": {"route": "capture", "item_type": "recipe"},
}
HEADER = "| metric | ollama:local-model | openrouter:cloud/model |"


def write_cases(directory: Path) -> Path:
    path = directory / "cases.jsonl"
    path.write_text("\n".join(json.dumps(case) for case in (TEXT_CASE, IMAGE_CASE)) + "\n")
    (directory / "images").mkdir()
    (directory / "images" / "card.png").write_bytes(b"fake png bytes")
    return path


def run_eval(rig: CliRig, *extra: str) -> str:
    cases = write_cases(rig.directory)
    return rig.run(
        "eval",
        "--providers",
        "ollama,openrouter",
        "--arms",
        "text,ocr",
        "--cases",
        str(cases),
        *extra,
    ).out


def test_eval_prints_a_comparison_table_with_a_column_for_each_provider(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    output = run_eval(rig)

    # Assert
    assert HEADER in output.splitlines()


def test_eval_saves_the_same_table_it_prints_to_the_out_path(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    saved = tmp_path / "reports" / "eval.md"

    # Execute
    output = run_eval(rig, "--out", str(saved))

    # Assert
    assert saved.read_text() == output


def test_eval_with_a_provider_that_is_not_configured_exits_2(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    cases = write_cases(tmp_path)

    # Execute
    result = rig.run("eval", "--providers", "ollama,groq", "--cases", str(cases))

    # Assert
    assert (result.exit_code, result.out, result.err) == (
        2,
        "",
        "provider groq is not configured\n",
    )


def test_eval_still_gets_answers_from_the_models_while_the_gpu_is_busy(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.smi.busy = True

    # Execute
    output = run_eval(rig)

    # Assert
    assert "| route accuracy | 100% | 100% |" in output.splitlines()


def test_eval_refuses_an_out_path_that_is_the_cases_file_before_asking_any_model(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    cases = write_cases(tmp_path)
    original = cases.read_text()

    # Execute
    result = rig.run("eval", "--providers", "ollama", "--cases", str(cases), "--out", str(cases))

    # Assert
    assert (result.exit_code, result.err, cases.read_text(), rig.providers.requests) == (
        2,
        f"--out {cases} is the cases file\n",
        original,
        [],
    )
