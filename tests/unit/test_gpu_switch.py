from datetime import timedelta

import pytest
from builders import BASE
from fakes.recording_unloader import RecordingUnloader
from fakes.store_factories import FreshStore
from gate_rig import CONFIG, a_gate, a_sample

from stash.gpu_switch import GpuSwitch, GpuSwitchResult

EXPIRY = BASE + timedelta(hours=CONFIG.manual_off_hours)


def a_switch(unloader: RecordingUnloader | None = None) -> tuple[GpuSwitch, RecordingUnloader]:
    unloader = unloader or RecordingUnloader()
    return GpuSwitch(a_gate(a_sample(), store=FreshStore()), unloader), unloader


def test_an_unexpected_unload_error_is_not_swallowed() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(RuntimeError("boom")))

    # Execute / Assert
    with pytest.raises(RuntimeError, match="boom"):
        switch.turn_off(BASE)


def test_a_result_with_a_blank_warning_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="warnings"):
        GpuSwitchResult(until=EXPIRY, warnings=(" ",))
