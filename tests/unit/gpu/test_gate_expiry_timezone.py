from zoneinfo import ZoneInfo

from builders import BASE, PLUS_FIVE
from fakes.memory_store import MemoryStore
from gate_rig import a_gate, a_sample

from stash.gpu.gate import GpuStatus


def test_the_expiry_is_shown_in_a_fixed_offset_timezone_of_now() -> None:
    # Setup
    gate = a_gate(a_sample())
    local_now = BASE.astimezone(PLUS_FIVE)
    gate.turn_off(local_now)

    # Execute
    status = gate.status(local_now)

    # Assert
    assert status.reason == "turned off until 21:00"


def test_the_expiry_is_shown_in_a_named_timezone_of_now() -> None:
    # Setup
    gate = a_gate(a_sample())
    pacific_now = BASE.astimezone(ZoneInfo("America/Los_Angeles"))
    gate.turn_off(pacific_now)

    # Execute
    status = gate.status(pacific_now)

    # Assert
    assert status.reason == "turned off until 08:00"


def test_the_expiry_is_shown_in_the_timezone_of_the_asking_now_not_the_turning_off_one() -> None:
    # Setup
    gate = a_gate(a_sample())
    gate.turn_off(BASE)

    # Execute
    status = gate.status(BASE.astimezone(PLUS_FIVE))

    # Assert
    assert status.reason == "turned off until 21:00"


def test_a_far_future_stored_expiry_is_ignored_for_a_caller_in_a_positive_offset_zone() -> None:
    # Setup
    store = MemoryStore()
    store.put_setting("gpu.manual_off_until", "9999-12-31T23:00:00+00:00")
    gate = a_gate(a_sample(), store=store)
    berlin_now = BASE.astimezone(ZoneInfo("Europe/Berlin"))

    # Execute
    status = gate.status(berlin_now)

    # Assert
    assert status == GpuStatus(busy=False, reason="GPU is free")
