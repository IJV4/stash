import pytest
from builders import NAIVE
from gate_rig import a_gate, a_sample

from stash.gpu.gate import GpuStatus


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
