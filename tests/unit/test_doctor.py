import pytest
from fakes.provider_probe import FakeProviderProbe

from stash.doctor import Doctor, DoctorCheck, DoctorLine
from stash.llm import ProbeResult

PASSING = ProbeResult(True, "fine")


def a_check(
    name: str = "database", required: bool = True, outcome: ProbeResult | BaseException = PASSING
) -> DoctorCheck:
    return DoctorCheck(name, required, FakeProviderProbe(outcome))


def test_a_line_with_a_blank_name_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="name"):
        DoctorLine(" ", ok=True, required=True, detail="fine")


def test_the_doctor_does_not_catch_a_keyboard_interrupt() -> None:
    # Setup
    doctor = Doctor([a_check("database", True, KeyboardInterrupt())])

    # Execute / Assert
    with pytest.raises(KeyboardInterrupt):
        doctor.run()
