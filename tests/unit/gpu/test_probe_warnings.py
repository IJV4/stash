import logging
import subprocess

import pytest
from smi_runner import FakeRunner

from stash.gpu.probe import NvidiaSmiProbe


def test_probe_warns_naming_the_error_class_when_nvidia_smi_exits_with_an_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=subprocess.CalledProcessError(9, "nvidia-smi")))

    # Execute
    probe.sample()

    # Assert
    assert [r.getMessage() for r in caplog.records] == ["nvidia-smi failed: CalledProcessError"]


def test_probe_warns_naming_the_error_class_when_nvidia_smi_times_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner(error=subprocess.TimeoutExpired("nvidia-smi", 10)))

    # Execute
    probe.sample()

    # Assert
    assert [r.getMessage() for r in caplog.records] == ["nvidia-smi failed: TimeoutExpired"]


def test_probe_warns_with_the_reason_when_the_output_is_not_understood(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner("No devices were found"))

    # Execute
    probe.sample()

    # Assert
    assert [r.getMessage() for r in caplog.records] == [
        "nvidia-smi output not understood: unreadable nvidia-smi row: 'No devices were found'"
    ]


def test_probe_clips_the_logged_reason_to_100_characters(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    probe = NvidiaSmiProbe(FakeRunner("x" * 500))

    # Execute
    probe.sample()

    # Assert
    assert "x" * 101 not in caplog.text


@pytest.mark.parametrize(
    "runner",
    [
        FakeRunner(error=FileNotFoundError("nvidia-smi")),
        FakeRunner(error=subprocess.CalledProcessError(9, "nvidia-smi")),
        FakeRunner(error=subprocess.TimeoutExpired("nvidia-smi", 10)),
        FakeRunner("garbage"),
    ],
)
def test_probe_logs_every_swallowed_failure_at_warning_level(
    runner: FakeRunner, caplog: pytest.LogCaptureFixture
) -> None:
    # Execute
    NvidiaSmiProbe(runner).sample()

    # Assert
    assert [r.levelno for r in caplog.records] == [logging.WARNING]
