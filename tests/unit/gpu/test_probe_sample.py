import subprocess

import pytest
from smi_runner import FakeRunner

from stash.gpu.probe import NvidiaSmiProbe


def test_probe_returns_none_when_nvidia_smi_exits_with_an_error() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=subprocess.CalledProcessError(9, "nvidia-smi")))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


def test_probe_returns_none_when_nvidia_smi_times_out() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=subprocess.TimeoutExpired("nvidia-smi", 10)))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


def test_probe_returns_none_when_the_output_is_garbage() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner("No devices were found"))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


def test_probe_returns_none_when_the_output_is_empty() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(""))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


def test_probe_does_not_swallow_unexpected_runner_errors() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=RuntimeError("bug")))

    # Execute / Assert
    with pytest.raises(RuntimeError):
        probe.sample()
