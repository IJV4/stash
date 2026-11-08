import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from builders import BASE
from fakes.recording_unloader import RecordingUnloader
from fakes.store_factories import FreshStore
from gate_rig import CONFIG, a_gate, a_sample
from log_records import recording_logs

from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitch, GpuSwitchResult
from stash.llm import LlmUnavailable

EXPIRY = BASE + timedelta(hours=CONFIG.manual_off_hours)
UNREACHABLE = "cannot reach Ollama at http://localhost:11434"


def a_switch(unloader: RecordingUnloader | None = None) -> tuple[GpuSwitch, RecordingUnloader]:
    unloader = unloader or RecordingUnloader()
    return GpuSwitch(a_gate(a_sample(), store=FreshStore()), unloader), unloader


def test_turning_off_reports_when_the_switch_expires() -> None:
    # Setup
    switch, _ = a_switch()

    # Execute
    result = switch.turn_off(BASE)

    # Assert
    assert result.until == EXPIRY


def test_turning_off_makes_the_gpu_busy_until_the_expiry() -> None:
    # Setup
    switch, _ = a_switch()

    # Execute
    switch.turn_off(BASE)

    # Assert
    assert switch.status(BASE) == GpuStatus(busy=True, reason="turned off until 16:00")


def test_turning_off_tells_the_model_to_unload() -> None:
    # Setup
    switch, unloader = a_switch()

    # Execute
    switch.turn_off(BASE)

    # Assert
    assert unloader.unloads == 1


def test_turning_off_reports_no_warnings_when_the_model_unloaded() -> None:
    # Setup
    switch, _ = a_switch()

    # Execute
    result = switch.turn_off(BASE)

    # Assert
    assert result.warnings == ()


def test_the_gate_is_already_off_when_the_model_is_told_to_unload() -> None:
    # Setup
    unloader = RecordingUnloader()
    switch, _ = a_switch(unloader)
    seen: list[GpuStatus] = []
    unloader.observers.append(lambda: seen.append(switch.status(BASE)))

    # Execute
    switch.turn_off(BASE)

    # Assert
    assert seen == [GpuStatus(busy=True, reason="turned off until 16:00")]


def test_an_unreachable_model_server_is_reported_in_the_result() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(LlmUnavailable(UNREACHABLE)))

    # Execute
    result = switch.turn_off(BASE)

    # Assert
    assert result == GpuSwitchResult(
        until=EXPIRY, warnings=(f"could not unload the model: {UNREACHABLE}",)
    )


def test_an_unreachable_model_server_does_not_keep_the_gpu_switched_on() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(LlmUnavailable(UNREACHABLE)))

    # Execute
    switch.turn_off(BASE)

    # Assert
    assert switch.status(BASE).busy is True


def test_an_unload_error_without_a_message_is_reported_by_its_type() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(LlmUnavailable()))

    # Execute
    result = switch.turn_off(BASE)

    # Assert
    assert result.warnings == ("could not unload the model: LlmUnavailable",)


def test_an_unexpected_unload_error_is_not_swallowed() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(RuntimeError("boom")))

    # Execute / Assert
    with pytest.raises(RuntimeError, match="boom"):
        switch.turn_off(BASE)


def test_turning_on_frees_the_gpu_again() -> None:
    # Setup
    switch, _ = a_switch()
    switch.turn_off(BASE)

    # Execute
    switch.turn_on()

    # Assert
    assert switch.status(BASE) == GpuStatus(busy=False, reason="GPU is free")


def test_turning_on_does_not_touch_the_model() -> None:
    # Setup
    switch, unloader = a_switch()

    # Execute
    switch.turn_on()

    # Assert
    assert unloader.unloads == 0


def test_the_status_of_a_free_gpu_is_the_gates_own_status() -> None:
    # Setup
    switch, _ = a_switch()

    # Execute
    status = switch.status(BASE)

    # Assert
    assert status == GpuStatus(busy=False, reason="GPU is free")


def test_a_result_with_a_blank_warning_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="warnings"):
        GpuSwitchResult(until=EXPIRY, warnings=(" ",))


def test_an_unreachable_model_server_is_logged_as_a_warning_naming_only_the_error_type() -> None:
    # Setup
    switch, _ = a_switch(RecordingUnloader(LlmUnavailable(UNREACHABLE)))

    # Execute
    with recording_logs("stash.gpu_switch") as logs:
        switch.turn_off(BASE)

    # Assert
    assert logs.entries() == [(logging.WARNING, "could not unload the model: LlmUnavailable")]


def test_a_successful_unload_logs_nothing() -> None:
    # Setup
    switch, _ = a_switch()

    # Execute
    with recording_logs("stash.gpu_switch") as logs:
        switch.turn_off(BASE)

    # Assert
    assert logs.entries() == []


def test_the_status_shows_the_expiry_in_the_timezone_of_the_given_now() -> None:
    # Setup
    switch, _ = a_switch()
    pacific_now = BASE.astimezone(ZoneInfo("America/Los_Angeles"))
    switch.turn_off(pacific_now)

    # Execute
    status = switch.status(pacific_now)

    # Assert
    assert status == GpuStatus(busy=True, reason="turned off until 08:00")
