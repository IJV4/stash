import subprocess
import sys

import pytest

from stash.gpu.probe import run_command


@pytest.mark.integration
def test_run_command_returns_the_standard_output_of_the_command() -> None:
    # Execute
    output = run_command([sys.executable, "-c", "print('x')"])

    # Assert
    assert output.strip() == "x"


@pytest.mark.integration
def test_run_command_for_a_missing_binary_raises_file_not_found_error() -> None:
    # Execute / Assert
    with pytest.raises(FileNotFoundError):
        run_command(["stash-no-such-binary-for-tests"])


@pytest.mark.integration
def test_run_command_for_a_failing_command_raises_called_process_error() -> None:
    # Execute / Assert
    with pytest.raises(subprocess.CalledProcessError):
        run_command([sys.executable, "-c", "raise SystemExit(3)"])


@pytest.mark.integration
def test_run_command_for_a_command_outliving_the_timeout_raises_timeout_expired() -> None:
    # Execute / Assert
    with pytest.raises(subprocess.TimeoutExpired):
        run_command([sys.executable, "-c", "import time; time.sleep(3)"], timeout_seconds=0.2)
