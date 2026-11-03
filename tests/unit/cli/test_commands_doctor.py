import io

import pytest
from fakes.provider_probe import FakeProviderProbe
from stash.cli.commands import run_doctor

from stash.doctor import Doctor, DoctorCheck
from stash.llm import ProbeResult


def a_doctor(ok: bool, required: bool = True) -> Doctor:
    outcome = ProbeResult(ok, "detail")
    return Doctor([DoctorCheck("database", required, FakeProviderProbe(outcome))])


def test_doctor_prints_the_rendered_report() -> None:
    # Setup
    out = io.StringIO()

    # Execute
    run_doctor(a_doctor(ok=True), out)

    # Assert
    assert out.getvalue() == "✔ database — detail\n"


@pytest.mark.parametrize(
    ("ok", "required", "expected_exit_code"),
    [(True, True, 0), (False, True, 1), (False, False, 0)],
    ids=["passing", "required-failure", "optional-failure"],
)
def test_doctor_exits_1_only_when_a_required_check_fails(
    ok: bool, required: bool, expected_exit_code: int
) -> None:
    # Execute
    exit_code = run_doctor(a_doctor(ok, required), io.StringIO())

    # Assert
    assert exit_code == expected_exit_code
