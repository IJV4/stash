import argparse

import pytest

from stash.cli.parser import MAX_LIMIT, GpuAction, build_parser
from stash.domain import ItemType, Stage
from stash.lifecycle import MAX_LIBRARY_LIMIT


def parse(*argv: str) -> argparse.Namespace:
    return build_parser().parse_args(list(argv))


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


def test_gpu_refuses_an_unknown_action() -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("gpu", "sideways")
    assert stop.value.code == 2


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


@pytest.mark.parametrize("limit", ["0", "-1", str(MAX_LIBRARY_LIMIT + 1), "many"])
def test_library_refuses_a_limit_outside_1_to_50(limit: str) -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("library", "--limit", limit)
    assert stop.value.code == 2


def test_library_names_the_allowed_limits_when_the_limit_is_too_big(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Execute
    with pytest.raises(SystemExit):
        parse("library", "--limit", "51")

    # Assert
    assert "invalid limit 51 (choose 1 to 50)" in capsys.readouterr().err


def test_library_refuses_an_unknown_type() -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("library", "--type", "spaceship")
    assert stop.value.code == 2


@pytest.mark.parametrize("days", ["0", "-1", "367", "soon", "99999999999999999999"])
def test_people_refuses_an_upcoming_window_that_is_not_1_to_366_days(days: str) -> None:
    # Execute / Assert
    with pytest.raises(SystemExit) as stop:
        parse("people", "--upcoming", days)
    assert stop.value.code == 2
