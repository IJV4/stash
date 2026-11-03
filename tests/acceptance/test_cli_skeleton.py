import pytest

from stash.cli import main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    # Setup
    argv = ["--version"]

    # Execute
    exit_code = main(argv)

    # Assert
    assert (exit_code, capsys.readouterr().out) == (0, "stash 0.1.0\n")
