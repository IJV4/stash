from dataclasses import replace

import pytest
from builders import BASE, NAIVE
from gate_rig import CONFIG, a_gate, a_sample

from stash.gpu.gate import NO_GPU_INFO, NO_GPU_READING, GpuStatus


def test_asking_the_status_with_a_naive_now_raises_value_error() -> None:
    # Setup
    gate = a_gate(a_sample())

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        gate.status(NAIVE)


def test_asking_is_busy_with_a_naive_now_raises_value_error() -> None:
    # Setup
    gate = a_gate(None)

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        gate.is_busy(NAIVE)


def test_turning_off_with_a_naive_now_raises_value_error() -> None:
    # Setup
    gate = a_gate(a_sample())

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        gate.turn_off(NAIVE)


def test_a_status_with_a_blank_reason_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        GpuStatus(busy=False, reason=" ")


def test_a_missing_gpu_reading_makes_the_gate_busy_by_default() -> None:
    # Setup
    gate = a_gate(None)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(True, NO_GPU_READING)


def test_a_missing_gpu_reading_is_free_when_the_config_says_so() -> None:
    # Setup
    gate = a_gate(None, config=replace(CONFIG, when_unreadable="free"))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(False, NO_GPU_INFO)


def test_the_manual_switch_still_wins_over_a_missing_reading() -> None:
    # Setup
    gate = a_gate(None)
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason.startswith("turned off until")
