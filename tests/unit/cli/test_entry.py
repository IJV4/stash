from pathlib import Path

import pytest
from app_builders import an_app
from cli_session import Session
from fakes.close_counter import CloseCounter
from fakes.failing_list_store import FailingListStore, ListFailed

from stash.app import StashApp
from stash.cli import main


def counter(app: StashApp) -> CloseCounter:
    assert isinstance(app.resources, CloseCounter)
    return app.resources


def test_the_app_is_closed_when_the_command_raises(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path, an_app(store=FailingListStore()))

    # Execute
    with pytest.raises(ListFailed):
        session.run("list", "--config", str(session.config_file))

    # Assert
    assert counter(session.app).closes == 1


def test_the_stash_config_variable_names_the_file_when_no_option_is_given(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path)
    env = {"STASH_CONFIG": str(session.config_file)}

    # Execute
    exit_code = session.run("retry", env=env)

    # Assert
    assert (exit_code, len(session.configs)) == (0, 1)


def test_the_default_file_under_home_is_read_when_nothing_else_names_one(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path)
    default = tmp_path / ".config" / "stash" / "stash.toml"
    default.parent.mkdir(parents=True)
    default.write_text(session.config_file.read_text())

    # Execute
    exit_code = session.run("retry")

    # Assert
    assert (exit_code, len(session.configs)) == (0, 1)


def test_a_missing_home_with_no_config_option_exits_2_without_building_an_app(
    tmp_path: Path,
) -> None:
    # Setup
    session = Session(tmp_path)

    # Execute
    exit_code = session.run("retry", env={})

    # Assert
    assert (exit_code, session.configs, "--config" in session.err.getvalue()) == (2, [], True)


def test_a_failed_command_prints_its_message_on_standard_error_and_returns_its_exit_code(
    tmp_path: Path,
) -> None:
    # Setup
    session = Session(tmp_path)
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")

    # Execute
    exit_code = session.run(
        "backup", "--to", str(blocker / "nas"), "--config", str(session.config_file)
    )

    # Assert
    assert (
        exit_code,
        session.out.getvalue(),
        session.err.getvalue().startswith("cannot write"),
    ) == (
        1,
        "",
        True,
    )


def test_a_failed_command_still_closes_the_app(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path)
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")

    # Execute
    session.run("backup", "--to", str(blocker / "nas"), "--config", str(session.config_file))

    # Assert
    assert counter(session.app).closes == 1


def test_a_usage_error_exits_2_and_prints_the_usage_on_the_given_error_stream(
    tmp_path: Path,
) -> None:
    # Setup
    session = Session(tmp_path)

    # Execute
    exit_code = session.run("list", "--limit", "0")

    # Assert
    assert (exit_code, session.out.getvalue(), session.err.getvalue().startswith("usage:")) == (
        2,
        "",
        True,
    )


def test_a_usage_error_builds_no_app(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path)

    # Execute
    session.run("list", "--limit", "0")

    # Assert
    assert session.configs == []


def test_without_an_injected_error_stream_a_usage_error_goes_to_standard_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Execute
    exit_code = main(["list", "--limit", "0"])

    # Assert
    assert (exit_code, capsys.readouterr().err.startswith("usage:")) == (2, True)
