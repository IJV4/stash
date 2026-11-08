from builders import BASE
from fakes.store_factories import FreshStore
from gate_rig import a_gate, a_sample

from stash.gpu.gate import GpuStatus


def test_a_corrupt_stored_switch_off_does_not_make_the_gate_busy() -> None:
    # Setup
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "next tuesday")
    gate = a_gate(a_sample(), store=store)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status == GpuStatus(busy=False, reason="GPU is free")


def test_a_stored_switch_off_without_an_offset_does_not_make_the_gate_busy() -> None:
    # Setup
    store = FreshStore()
    store.put_setting("gpu.manual_off_until", "2026-11-02T16:00:00")
    gate = a_gate(a_sample(), store=store)

    # Execute
    busy = gate.is_busy(BASE)

    # Assert
    assert busy is False
