import argparse
from pathlib import Path

import pytest

from stash.cli.parser import MAX_LIMIT, Command, GpuAction, build_parser
from stash.config import Thinking
from stash.domain import ItemType, Stage
from stash.evaluation import EvalArm


def parse(*argv: str) -> argparse.Namespace:
    return build_parser().parse_args(list(argv))


def test_list_defaults_to_no_filters_and_a_limit_of_20() -> None:
    # Execute
    arguments = parse("list")

    # Assert
    assert (arguments.stage, arguments.item_type, arguments.limit) == (None, None, 20)


def test_list_takes_a_stage_a_type_and_a_limit() -> None:
    # Execute
    arguments = parse("list", "--stage", "want_to", "--type", "place", "--limit", "5")

    # Assert
    assert (arguments.stage, arguments.item_type, arguments.limit) == ("want_to", "place", 5)


@pytest.mark.parametrize("stage", [stage.value for stage in Stage])
def test_list_accepts_every_stage(stage: str) -> None:
    # Execute
    arguments = parse("list", "--stage", stage)

    # Assert
    assert arguments.stage == stage


@pytest.mark.parametrize("item_type", [item_type.value for item_type in ItemType])
def test_list_accepts_every_item_type(item_type: str) -> None:
    # Execute
    arguments = parse("list", "--type", item_type)

    # Assert
    assert arguments.item_type == item_type


@pytest.mark.parametrize(
    "argv",
    [
        ["list", "--stage", "nowhere"],
        ["list", "--type", "spaceship"],
        ["list", "--limit", "0"],
        ["list", "--limit", "-3"],
        ["list", "--limit", "many"],
    ],
    ids=["stage", "type", "zero-limit", "negative-limit", "non-numeric-limit"],
)
def test_list_refuses_values_outside_its_choices(argv: list[str]) -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse(*argv)
    assert stop.value.code == 2


@pytest.mark.parametrize(
    "argv",
    [["doctor"], ["list"], ["retry"], ["gpu", "status"], ["eval"], ["backup", "--to", "d"]],
    ids=lambda argv: argv[0],
)
def test_every_subcommand_takes_a_config_path(argv: list[str]) -> None:
    # Execute
    arguments = parse(*argv, "--config", "/tmp/stash.toml")

    # Assert
    assert arguments.config == "/tmp/stash.toml"


def test_the_config_path_is_absent_when_not_given() -> None:
    # Execute
    arguments = parse("doctor")

    # Assert
    assert arguments.config is None


@pytest.mark.parametrize("action", ["status", "off", "on"])
def test_gpu_takes_status_off_or_on(action: str) -> None:
    # Execute
    arguments = parse("gpu", action)

    # Assert
    assert (arguments.command, arguments.action) == ("gpu", action)


def test_gpu_refuses_an_unknown_action() -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("gpu", "sideways")
    assert stop.value.code == 2


def test_eval_defaults_to_every_configured_provider_every_arm_and_the_shipped_cases() -> None:
    # Execute
    arguments = parse("eval")

    # Assert
    assert (arguments.providers, arguments.arms, arguments.cases, arguments.out) == (
        None,
        tuple(EvalArm),
        Path("evals/cases.jsonl"),
        None,
    )


def test_eval_reads_comma_separated_providers_and_arms() -> None:
    # Execute
    arguments = parse("eval", "--providers", "ollama, openrouter", "--arms", "text,ocr")

    # Assert
    assert (arguments.providers, arguments.arms) == (
        ("ollama", "openrouter"),
        (EvalArm.TEXT, EvalArm.OCR),
    )


def test_eval_refuses_an_unknown_arm_naming_it(capsys: pytest.CaptureFixture[str]) -> None:
    # Execute
    with pytest.raises(SystemExit) as stop:
        parse("eval", "--arms", "text,telepathy")

    # Assert
    assert (stop.value.code, "unknown arm telepathy" in capsys.readouterr().err) == (2, True)


@pytest.mark.parametrize("providers", ["", "ollama,,openrouter"])
def test_eval_refuses_an_empty_provider_name(providers: str) -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("eval", "--providers", providers)
    assert stop.value.code == 2


def test_eval_defaults_to_no_thinking_choice() -> None:
    # Execute
    arguments = parse("eval")

    # Assert
    assert arguments.thinking is None


def test_eval_reads_comma_separated_thinking_values_in_the_order_given() -> None:
    # Execute
    arguments = parse("eval", "--thinking", "off, default")

    # Assert
    assert arguments.thinking == (Thinking.OFF, Thinking.DEFAULT)


def test_eval_refuses_an_unknown_thinking_value_naming_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Execute
    with pytest.raises(SystemExit):
        parse("eval", "--thinking", "default,deep")

    # Assert
    assert "unknown thinking deep (choose from default, off)" in capsys.readouterr().err


def test_eval_refuses_an_unknown_arm_with_the_choices(capsys: pytest.CaptureFixture[str]) -> None:
    # Execute
    with pytest.raises(SystemExit):
        parse("eval", "--arms", "telepathy")

    # Assert
    assert "unknown arm telepathy (choose from text, vision, ocr)" in capsys.readouterr().err


@pytest.mark.parametrize("thinking", ["", "off,,default"])
def test_eval_refuses_an_empty_thinking_value(thinking: str) -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("eval", "--thinking", thinking)
    assert stop.value.code == 2


def test_eval_takes_a_cases_file_and_an_out_path() -> None:
    # Execute
    arguments = parse("eval", "--cases", "mine.jsonl", "--out", "report.md")

    # Assert
    assert (arguments.cases, arguments.out) == (Path("mine.jsonl"), Path("report.md"))


def test_backup_needs_a_target_directory() -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("backup")
    assert stop.value.code == 2


def test_backup_takes_the_target_directory() -> None:
    # Execute
    arguments = parse("backup", "--to", "/mnt/nas")

    # Assert
    assert arguments.to == Path("/mnt/nas")


def test_a_command_is_required() -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse()
    assert stop.value.code == 2


def test_the_version_flag_prints_the_version_and_exits_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Execute
    with pytest.raises(SystemExit) as stop:
        parse("--version")

    # Assert
    assert (stop.value.code, capsys.readouterr().out) == (0, "stash 0.1.0\n")


def test_list_gives_the_stage_as_a_stage() -> None:
    # Execute
    arguments = parse("list", "--stage", "want_to")

    # Assert
    assert arguments.stage is Stage.WANT_TO


def test_list_gives_the_type_as_an_item_type() -> None:
    # Execute
    arguments = parse("list", "--type", "place")

    # Assert
    assert arguments.item_type is ItemType.PLACE


def test_gpu_gives_the_action_as_a_gpu_action() -> None:
    # Execute
    arguments = parse("gpu", "off")

    # Assert
    assert arguments.action is GpuAction.OFF


@pytest.mark.parametrize("command", list(Command))
def test_every_command_is_a_subcommand_of_the_parser(command: Command) -> None:
    # Setup
    required = {Command.BACKUP: ["--to", "d"], Command.GPU: ["on"]}

    # Execute
    arguments = parse(command.value, *required.get(command, []))

    # Assert
    assert Command(arguments.command) is command


@pytest.mark.parametrize(
    ("argv", "allowed"),
    [
        (["list", "--stage", "nowhere"], [stage.value for stage in Stage]),
        (["list", "--type", "spaceship"], [kind.value for kind in ItemType]),
        (["gpu", "sideways"], [action.value for action in GpuAction]),
    ],
    ids=["stage", "type", "gpu-action"],
)
def test_a_value_outside_the_choices_is_refused_naming_every_allowed_value(
    argv: list[str], allowed: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    # Execute
    with pytest.raises(SystemExit):
        parse(*argv)

    # Assert
    error = capsys.readouterr().err.splitlines()[-1]
    assert all(value in error for value in allowed)


def test_list_accepts_the_largest_limit() -> None:
    # Execute
    arguments = parse("list", "--limit", str(MAX_LIMIT))

    # Assert
    assert arguments.limit == MAX_LIMIT


@pytest.mark.parametrize("limit", [str(MAX_LIMIT + 1), "99999999999999999999"])
def test_list_refuses_a_limit_above_the_maximum_naming_the_choices(
    capsys: pytest.CaptureFixture[str], limit: str
) -> None:
    # Execute
    with pytest.raises(SystemExit) as stop:
        parse("list", "--limit", limit)

    # Assert
    message = f"invalid limit {limit} (choose 1 to 1000)"
    assert (stop.value.code, message in capsys.readouterr().err) == (2, True)
