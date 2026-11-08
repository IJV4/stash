from datetime import timedelta

from builders import BASE
from fakes.store_factories import FreshStore
from gate_rig import a_gate, a_sample

from stash.config import GpuConfig
from stash.gpu.gate import GpuStatus


def test_a_manual_switch_off_makes_the_gate_busy_until_the_expiry_time() -> None:
    # Setup
    gate = a_gate(a_sample())
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE + timedelta(hours=1))

    # Assert
    assert status == GpuStatus(busy=True, reason="turned off until 16:00")


def test_the_manual_switch_off_beats_a_free_gpu() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=0, utilization_pct=0))
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.busy is True


def test_the_manual_switch_off_beats_no_gpu_information() -> None:
    # Setup
    gate = a_gate(None)
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason == "turned off until 16:00"


def test_the_manual_switch_off_is_reported_before_vram_pressure() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=9000))
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE)

    # Assert
    assert status.reason == "turned off until 16:00"


def test_an_expired_switch_off_leaves_a_free_gpu_free() -> None:
    # Setup
    gate = a_gate(a_sample())
    expiry = gate.turn_off(BASE)

    # Execute
    status = gate.status(expiry)

    # Assert
    assert status == GpuStatus(busy=False, reason="GPU is free")


def test_an_expired_switch_off_hands_over_to_the_vram_rule() -> None:
    # Setup
    gate = a_gate(a_sample(used_mib=9000))
    expiry = gate.turn_off(BASE)

    # Execute
    status = gate.status(expiry)

    # Assert
    assert status.reason == "other apps use 9000 MiB"


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


def test_turning_on_cancels_the_manual_switch_off() -> None:
    # Setup
    gate = a_gate(a_sample())
    gate.turn_off(BASE)
    gate.turn_on()

    # Execute
    status = gate.status(BASE + timedelta(hours=1))

    # Assert
    assert status.busy is False


def test_turning_on_without_a_previous_switch_off_changes_nothing() -> None:
    # Setup
    gate = a_gate(a_sample())

    # Execute
    gate.turn_on()

    # Assert
    assert gate.status(BASE).busy is False


def test_turning_off_returns_an_expiry_four_hours_from_now() -> None:
    # Setup
    gate = a_gate(a_sample())

    # Execute
    expiry = gate.turn_off(BASE)

    # Assert
    assert expiry == BASE + timedelta(hours=4)


def test_turning_off_uses_the_configured_number_of_hours() -> None:
    # Setup
    gate = a_gate(a_sample(), config=GpuConfig(manual_off_hours=1.5))

    # Execute
    expiry = gate.turn_off(BASE)

    # Assert
    assert expiry == BASE + timedelta(minutes=90)


def test_a_new_gate_on_the_same_store_is_still_switched_off() -> None:
    # Setup
    store = FreshStore()
    a_gate(a_sample(), store=store).turn_off(BASE)
    restarted = a_gate(a_sample(), store=store)

    # Execute
    status = restarted.status(BASE + timedelta(hours=1))

    # Assert
    assert status.reason == "turned off until 16:00"


def test_a_new_gate_on_the_same_store_stays_on_after_turning_on() -> None:
    # Setup
    store = FreshStore()
    first = a_gate(a_sample(), store=store)
    first.turn_off(BASE)
    first.turn_on()
    restarted = a_gate(a_sample(), store=store)

    # Execute
    status = restarted.status(BASE + timedelta(hours=1))

    # Assert
    assert status.busy is False
