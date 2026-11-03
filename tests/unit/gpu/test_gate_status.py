import pytest
from builders import BASE, NAIVE
from fakes.gpu import FakeGpuProbe, FakeOwnVram
from fakes.memory_store import MemoryStore
from gate_rig import CONFIG, a_gate, a_sample

from stash.gpu.gate import GpuGate, GpuStatus


def test_is_busy_is_true_when_the_status_is_busy() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=9000))

    # Execute
    busy = gate.is_busy(BASE)

    # Assert
    assert busy is True


def test_is_busy_is_false_when_the_status_is_free() -> None:
    # Setup
    gate = a_gate(a_sample())

    # Execute
    busy = gate.is_busy(BASE)

    # Assert
    assert busy is False


def test_is_busy_is_true_while_switched_off() -> None:
    # Setup
    gate = a_gate(a_sample())
    gate.turn_off(BASE)

    # Execute
    busy = gate.is_busy(BASE)

    # Assert
    assert busy is True


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


def test_own_vram_is_asked_once_when_there_is_a_sample() -> None:
    # Setup
    own = FakeOwnVram()
    gate = GpuGate(FakeGpuProbe(a_sample()), own, MemoryStore(), CONFIG)

    # Execute
    gate.status(BASE)

    # Assert
    assert own.calls == 1


def test_own_vram_is_not_asked_when_there_is_no_sample() -> None:
    # Setup
    own = FakeOwnVram()
    gate = GpuGate(FakeGpuProbe(None), own, MemoryStore(), CONFIG)

    # Execute
    gate.status(BASE)

    # Assert
    assert own.calls == 0


def test_own_vram_is_not_asked_while_switched_off() -> None:
    # Setup
    own = FakeOwnVram()
    gate = GpuGate(FakeGpuProbe(a_sample()), own, MemoryStore(), CONFIG)
    gate.turn_off(BASE)

    # Execute
    gate.status(BASE)

    # Assert
    assert own.calls == 0


def test_status_cannot_be_modified() -> None:
    # Setup
    status = GpuStatus(busy=False, reason="GPU is free")

    # Execute / Assert
    with pytest.raises(AttributeError):
        status.busy = True  # type: ignore[misc]


def test_a_status_with_a_blank_reason_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        GpuStatus(busy=False, reason=" ")
