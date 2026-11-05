from pathlib import Path

from cli_rig import CliRig, build_cli_rig
from eval_files import write_cases
from fakes.fake_providers import OLLAMA_CHAT_PATH, thinking_fields

TEXT_CASE = {
    "id": "t01",
    "arm": "text",
    "text": "Ichiran ramen in Fukuoka",
    "link": None,
    "expect": {"route": "capture", "item_type": "place"},
}
T10_CASE = {
    "id": "t10",
    "arm": "text",
    "text": "Date night at the Harbor Jazz Club on 2027-03-14 at 8pm",
    "link": None,
    "expect": {"route": "capture", "stage": "planned", "date": "2027-03-14"},
}
IMAGE_CASE = {
    "id": "i01",
    "arm": "image",
    "text": "save this",
    "image": "card.png",
    "expect": {"route": "capture", "item_type": "recipe"},
}
HEADER = (
    "| metric | ollama:local-model thinking=default | openrouter:cloud/model thinking=default |"
)
COMPARISON_HEADER = (
    "| metric | ollama:local-model thinking=default | ollama:local-model thinking=off |"
)
FOUR_COLUMN_HEADER = (
    "| metric | ollama:local-model thinking=default | ollama:local-model thinking=off"
    " | openrouter:cloud/model thinking=default | openrouter:cloud/model thinking=off |"
)
VISION_MODEL = "local-vision"


def run_eval(rig: CliRig, *extra: str) -> str:
    cases = write_cases(rig.directory, TEXT_CASE, IMAGE_CASE)
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
    cases = write_cases(tmp_path, TEXT_CASE, IMAGE_CASE)

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
    cases = write_cases(tmp_path, TEXT_CASE, IMAGE_CASE)
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


def run_thinking_eval(rig: CliRig, *extra: str, cases: tuple[dict[str, object], ...]) -> str:
    path = write_cases(rig.directory, *cases)
    return rig.run("eval", "--providers", "ollama", "--cases", str(path), *extra).out


def thinking_comparison(rig: CliRig) -> str:
    return run_thinking_eval(
        rig,
        "--arms",
        "text",
        "--thinking",
        "default,off",
        cases=(TEXT_CASE, T10_CASE),
    )


def reasoning_efforts_sent(rig: CliRig) -> list[object]:
    return [body.get("reasoning_effort") for body in rig.providers.chat_bodies(OLLAMA_CHAT_PATH)]


def models_and_efforts_sent(rig: CliRig) -> list[tuple[object, object]]:
    return [
        (body["model"], body.get("reasoning_effort"))
        for body in rig.providers.chat_bodies(OLLAMA_CHAT_PATH)
    ]


def thinking_fields_sent(rig: CliRig) -> list[dict[str, object]]:
    return [thinking_fields(body) for body in rig.providers.chat_bodies(OLLAMA_CHAT_PATH)]


def test_eval_with_thinking_default_and_off_prints_a_column_for_each(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    output = thinking_comparison(rig)

    # Assert
    assert COMPARISON_HEADER in output.splitlines()


def test_eval_with_thinking_default_and_off_sends_the_off_field_only_on_the_off_run(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    thinking_comparison(rig)

    # Assert
    assert reasoning_efforts_sent(rig) == [None, None, "none", "none"]


def test_eval_lists_a_failing_case_with_its_wanted_and_got_values(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    output = thinking_comparison(rig)

    # Assert
    assert (
        "t10 text FAIL stage: want planned got want_to; date: want 2027-03-14 got none"
        in output.split("### cases — ollama:local-model thinking=default\n")[1]
    )


def test_eval_with_two_providers_and_two_thinking_values_prints_providers_outer_thinking_inner(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    cases = write_cases(rig.directory, TEXT_CASE)

    # Execute
    output = rig.run(
        "eval",
        "--providers",
        "ollama,openrouter",
        "--arms",
        "text",
        "--thinking",
        "default,off",
        "--cases",
        str(cases),
    ).out

    # Assert
    assert FOUR_COLUMN_HEADER in output.splitlines()


def test_eval_thinking_flag_off_labels_the_run_off_when_the_config_sets_nothing(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    output = run_thinking_eval(rig, "--arms", "text", "--thinking", "off", cases=(TEXT_CASE,))

    # Assert
    assert "| metric | ollama:local-model thinking=off |" in output.splitlines()


def test_eval_thinking_flag_off_sends_the_off_field_when_the_config_sets_nothing(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    run_thinking_eval(rig, "--arms", "text", "--thinking", "off", cases=(TEXT_CASE,))

    # Assert
    assert reasoning_efforts_sent(rig) == ["none"]


def test_eval_without_the_thinking_flag_labels_the_run_with_the_configured_filing_thinking(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, filing_thinking="off")

    # Execute
    output = run_thinking_eval(rig, "--arms", "text", cases=(TEXT_CASE,))

    # Assert
    assert "| metric | ollama:local-model thinking=off |" in output.splitlines()


def test_eval_without_the_thinking_flag_sends_the_configured_filing_thinking(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, filing_thinking="off")

    # Execute
    run_thinking_eval(rig, "--arms", "text", cases=(TEXT_CASE,))

    # Assert
    assert reasoning_efforts_sent(rig) == ["none"]


def test_eval_thinking_flag_default_labels_the_run_default_over_a_configured_off(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, filing_thinking="off")

    # Execute
    output = run_thinking_eval(rig, "--arms", "text", "--thinking", "default", cases=(TEXT_CASE,))

    # Assert
    assert "| metric | ollama:local-model thinking=default |" in output.splitlines()


def test_eval_thinking_flag_default_sends_no_thinking_field_over_a_configured_off(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, filing_thinking="off")

    # Execute
    run_thinking_eval(rig, "--arms", "text", "--thinking", "default", cases=(TEXT_CASE,))

    # Assert
    assert thinking_fields_sent(rig) == [{}]


def test_eval_thinking_off_sends_the_off_field_to_the_vision_model(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, vision_model=VISION_MODEL)

    # Execute
    run_thinking_eval(rig, "--arms", "vision", "--thinking", "off", cases=(IMAGE_CASE,))

    # Assert
    assert models_and_efforts_sent(rig) == [(VISION_MODEL, "none")]


def test_eval_thinking_off_sends_the_off_field_when_the_vision_arm_falls_back_to_the_text_model(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    run_thinking_eval(rig, "--arms", "vision", "--thinking", "off", cases=(IMAGE_CASE,))

    # Assert
    assert models_and_efforts_sent(rig) == [("local-model", "none")]


def test_eval_labels_the_vision_arm_run_with_the_vision_model(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, vision_model=VISION_MODEL)

    # Execute
    output = run_thinking_eval(rig, "--arms", "vision", "--thinking", "off", cases=(IMAGE_CASE,))

    # Assert
    assert "| metric | ollama:local-model vision=local-vision thinking=off |" in output.splitlines()
