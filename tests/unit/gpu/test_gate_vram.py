from builders import BASE
from gate_rig import TOTAL, USED_WHEN_FREE_EQUALS_MINIMUM, a_gate, a_sample

from stash.config import GpuConfig
from stash.gpu.gate import GpuStatus


def test_a_gpu_with_plenty_of_free_vram_and_low_utilization_is_free() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=1000, utilization_pct=5))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(busy=False, reason="GPU is free")


def test_no_gpu_information_is_free() -> None:
    # Setup
    gate = a_gate(None)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(busy=False, reason="no GPU info")


def test_free_vram_exactly_at_the_minimum_is_free() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=USED_WHEN_FREE_EQUALS_MINIMUM))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False


def test_free_vram_one_mib_below_the_minimum_is_busy() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=USED_WHEN_FREE_EQUALS_MINIMUM + 1))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is True


def test_busy_for_vram_names_the_foreign_usage_in_the_reason() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=8000))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason == "other apps use 8000 MiB"


def test_own_vram_is_excluded_from_the_foreign_usage_in_the_reason() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=9000), own_mib=1000)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason == "other apps use 8000 MiB"


def test_own_vram_keeps_the_gpu_free_when_only_it_fills_the_gpu() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=9000), own_mib=9000)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False


def test_own_vram_larger_than_used_vram_is_treated_as_no_foreign_usage() -> None:
    # Setup
    config = GpuConfig(min_free_vram_mib=TOTAL, max_foreign_utilization_pct=50)
    gate = a_gate(a_sample(used_mib=1000), own_mib=5000, config=config)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False
