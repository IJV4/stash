import io
from zoneinfo import ZoneInfo

from builders import BASE
from fakes.recording_unloader import RecordingUnloader
from gate_rig import a_gate, a_sample

from stash.cli.commands import gpu_off, gpu_on, gpu_status
from stash.gpu_switch import GpuSwitch
from stash.llm import LlmUnavailable

LOS_ANGELES = ZoneInfo("America/Los_Angeles")


def a_switch(unloader: RecordingUnloader | None = None) -> GpuSwitch:
    return GpuSwitch(a_gate(a_sample()), RecordingUnloader() if unloader is None else unloader)


def test_gpu_status_prints_free_when_nothing_uses_the_gpu() -> None:
    # Setup
    out = io.StringIO()

    # Execute
    exit_code = gpu_status(a_switch(), BASE, LOS_ANGELES, out)

    # Assert
    assert (exit_code, out.getvalue()) == (0, "GPU free — GPU is free\n")


def test_gpu_off_prints_the_expiry_in_the_timezone_of_the_given_time() -> None:
    # Setup
    out = io.StringIO()

    # Execute
    exit_code = gpu_off(a_switch(), BASE, LOS_ANGELES, out)

    # Assert
    assert (exit_code, out.getvalue()) == (0, "GPU switched off until 08:00\n")


def test_gpu_off_tells_the_model_to_unload() -> None:
    # Setup
    unloader = RecordingUnloader()

    # Execute
    gpu_off(a_switch(unloader), BASE, LOS_ANGELES, io.StringIO())

    # Assert
    assert unloader.unloads == 1


def test_gpu_off_adds_a_line_and_still_exits_0_when_the_model_could_not_be_unloaded() -> None:
    # Setup
    out = io.StringIO()
    switch = a_switch(RecordingUnloader(LlmUnavailable("cannot reach Ollama")))

    # Execute
    exit_code = gpu_off(switch, BASE, LOS_ANGELES, out)

    # Assert
    assert (exit_code, out.getvalue()) == (
        0,
        "GPU switched off until 08:00\n! could not unload the model: cannot reach Ollama\n",
    )


def test_gpu_status_after_off_reads_busy_until_the_expiry() -> None:
    # Setup
    switch = a_switch()
    gpu_off(switch, BASE, LOS_ANGELES, io.StringIO())
    out = io.StringIO()

    # Execute
    gpu_status(switch, BASE, LOS_ANGELES, out)

    # Assert
    assert out.getvalue() == "GPU busy — turned off until 08:00\n"


def test_gpu_on_prints_switched_on_and_ends_the_switch_off() -> None:
    # Setup
    switch = a_switch()
    gpu_off(switch, BASE, LOS_ANGELES, io.StringIO())
    out = io.StringIO()

    # Execute
    exit_code = gpu_on(switch, out)

    # Assert
    assert (exit_code, out.getvalue(), switch.status(BASE).busy) == (0, "GPU switched on\n", False)
