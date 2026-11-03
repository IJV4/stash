from builders import BASE
from gate_rig import TOTAL, a_gate, a_sample

from stash.config import GpuConfig
from stash.gpu.gate import GpuStatus


def test_foreign_utilization_exactly_at_the_maximum_is_free() -> None:
    # Setup
    gate = a_gate(a_sample(utilization_pct=50))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False


def test_foreign_utilization_one_point_above_the_maximum_is_busy() -> None:
    # Setup
    gate = a_gate(a_sample(utilization_pct=51))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(busy=True, reason="GPU 51% busy")


def test_high_utilization_is_free_while_stash_has_its_own_model_loaded() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=1000, utilization_pct=100), own_mib=1000)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False


def test_vram_pressure_is_reported_before_high_utilization() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=8000, utilization_pct=100))

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason == "other apps use 8000 MiB"


def test_the_configured_thresholds_decide_not_built_in_ones() -> None:
    # Setup
    config = GpuConfig(min_free_vram_mib=0, max_foreign_utilization_pct=100)
    gate = a_gate(a_sample(used_mib=TOTAL, utilization_pct=100), config=config)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is False
