import subprocess

import pytest
from smi_runner import SMI_OUTPUT, FakeRunner

from stash.gpu.port import GpuSample
from stash.gpu.probe import NvidiaSmiProbe


def test_probe_returns_the_sample_parsed_from_the_runner_output() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(SMI_OUTPUT))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample == GpuSample(12288, 1024, 3)


def test_probe_runs_the_nvidia_smi_csv_query_command() -> None:
    # Setup
    runner = FakeRunner()

    # Execute
    NvidiaSmiProbe(runner).sample()

    # Assert
    assert runner.calls == [
        (
            "nvidia-smi",
            "--query-gpu=memory.total,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        )
    ]


def test_probe_returns_none_when_nvidia_smi_is_not_installed() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=FileNotFoundError("nvidia-smi")))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


def test_probe_returns_none_when_the_runner_fails_with_another_os_error() -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=PermissionError("nvidia-smi")))

    # Execute
    sample = probe.sample()

    # Assert
    assert sample is None


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
