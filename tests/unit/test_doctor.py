import logging
from dataclasses import FrozenInstanceError

import pytest
from fakes.provider_probe import FakeProviderProbe
from log_records import recording_logs

from stash.doctor import Doctor, DoctorCheck, DoctorLine, DoctorReport
from stash.llm import ProbeResult

PASSING = ProbeResult(True, "fine")
FAILING = ProbeResult(False, "broken")


def a_check(
    name: str = "database", required: bool = True, outcome: ProbeResult | BaseException = PASSING
) -> DoctorCheck:
    return DoctorCheck(name, required, FakeProviderProbe(outcome))


def a_line(ok: bool = True, required: bool = True, name: str = "database") -> DoctorLine:
    return DoctorLine(name=name, ok=ok, required=required, detail="detail")


def test_a_check_with_a_blank_name_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="name"):
        a_check(name=" ")


def test_a_check_cannot_be_modified() -> None:
    # Setup
    check = a_check()

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        check.required = False  # type: ignore[misc]


@pytest.mark.parametrize(
    ("ok", "required", "symbol"),
    [(True, True, "✔"), (True, False, "✔"), (False, True, "✖"), (False, False, "!")],
)
def test_a_line_shows_a_tick_a_cross_for_required_failures_and_a_bang_for_optional_ones(
    ok: bool, required: bool, symbol: str
) -> None:
    # Execute
    line = a_line(ok=ok, required=required)

    # Assert
    assert line.symbol == symbol


@pytest.mark.parametrize(
    ("ok", "required", "blocks"),
    [(True, True, False), (True, False, False), (False, True, True), (False, False, False)],
)
def test_a_line_blocks_only_when_a_required_check_failed(
    ok: bool, required: bool, blocks: bool
) -> None:
    # Execute
    line = a_line(ok=ok, required=required)

    # Assert
    assert line.blocks is blocks


def test_a_line_renders_its_symbol_name_and_detail() -> None:
    # Setup
    line = DoctorLine("openrouter", ok=False, required=True, detail="invalid key")

    # Execute
    rendered = line.render()

    # Assert
    assert rendered == "✖ openrouter — invalid key"


def test_a_line_with_a_blank_name_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="name"):
        DoctorLine(" ", ok=True, required=True, detail="fine")


def test_a_line_with_a_blank_detail_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="detail"):
        DoctorLine("database", ok=True, required=True, detail=" ")


def test_a_report_is_blocked_when_any_line_blocks() -> None:
    # Setup
    report = DoctorReport((a_line(), a_line(ok=False)))

    # Execute / Assert
    assert report.blocked is True


def test_a_report_with_only_optional_failures_is_not_blocked() -> None:
    # Setup
    report = DoctorReport((a_line(), a_line(ok=False, required=False)))

    # Execute / Assert
    assert report.blocked is False


def test_an_empty_report_is_not_blocked() -> None:
    # Execute / Assert
    assert DoctorReport(()).blocked is False


def test_a_blocked_report_exits_with_one() -> None:
    # Execute / Assert
    assert DoctorReport((a_line(ok=False),)).exit_code == 1


def test_a_report_that_is_not_blocked_exits_with_zero() -> None:
    # Execute / Assert
    assert DoctorReport((a_line(), a_line(ok=False, required=False))).exit_code == 0


def test_a_report_renders_one_line_per_check_without_a_trailing_newline() -> None:
    # Setup
    report = DoctorReport((a_line(name="config"), a_line(ok=False, required=False, name="deno")))

    # Execute
    rendered = report.render()

    # Assert
    assert rendered == "✔ config — detail\n! deno — detail"


def test_an_empty_report_renders_nothing() -> None:
    # Execute / Assert
    assert DoctorReport(()).render() == ""


def test_running_the_doctor_reports_each_check_with_its_verdict_and_detail() -> None:
    # Setup
    doctor = Doctor([a_check("ollama", True, FAILING), a_check("deno", False, PASSING)])

    # Execute
    report = doctor.run()

    # Assert
    assert report.lines == (
        DoctorLine("ollama", ok=False, required=True, detail="broken"),
        DoctorLine("deno", ok=True, required=False, detail="fine"),
    )


def test_running_the_doctor_keeps_the_order_the_checks_were_given_in() -> None:
    # Setup
    names = ["config", "database", "ollama", "openrouter", "nvidia-smi"]
    doctor = Doctor([a_check(name) for name in names])

    # Execute
    report = doctor.run()

    # Assert
    assert [line.name for line in report.lines] == names


def test_a_check_that_raises_becomes_a_failed_line_with_the_error_type_and_message() -> None:
    # Setup
    doctor = Doctor([a_check("database", True, RuntimeError("disk is on fire"))])

    # Execute
    report = doctor.run()

    # Assert
    assert report.lines == (
        DoctorLine("database", ok=False, required=True, detail="RuntimeError: disk is on fire"),
    )


@pytest.mark.parametrize("error", [TimeoutError(), KeyError(), ValueError("  ")])
def test_a_check_that_raises_with_a_blank_message_is_reported_by_its_type_alone(
    error: Exception,
) -> None:
    # Setup
    doctor = Doctor([a_check("database", True, error)])

    # Execute
    [line] = doctor.run().lines

    # Assert
    assert line.detail == type(error).__name__


def test_a_check_that_raises_does_not_stop_the_checks_after_it() -> None:
    # Setup
    doctor = Doctor([a_check("first", True, RuntimeError("boom")), a_check("second")])

    # Execute
    report = doctor.run()

    # Assert
    assert [line.name for line in report.lines] == ["first", "second"]


def test_a_required_check_that_raises_blocks_the_report() -> None:
    # Setup
    doctor = Doctor([a_check("database", True, RuntimeError("boom"))])

    # Execute
    report = doctor.run()

    # Assert
    assert report.exit_code == 1


def test_an_optional_check_that_raises_does_not_block_the_report() -> None:
    # Setup
    doctor = Doctor([a_check("deno", False, RuntimeError("boom"))])

    # Execute
    report = doctor.run()

    # Assert
    assert report.exit_code == 0


def test_a_check_that_raises_is_logged_with_its_name() -> None:
    # Setup
    doctor = Doctor([a_check("database", True, RuntimeError("boom"))])

    # Execute
    with recording_logs("stash.doctor") as recorder:
        doctor.run()

    # Assert
    assert recorder.entries() == [(logging.ERROR, "doctor check database raised")]


def test_the_doctor_does_not_catch_a_keyboard_interrupt() -> None:
    # Setup
    doctor = Doctor([a_check("database", True, KeyboardInterrupt())])

    # Execute / Assert
    with pytest.raises(KeyboardInterrupt):
        doctor.run()


def test_a_mandatory_check_is_a_required_check() -> None:
    # Setup
    probe = FakeProviderProbe(PASSING)

    # Execute
    check = DoctorCheck.mandatory("database", probe)

    # Assert
    assert check == DoctorCheck("database", True, probe)


def test_an_optional_check_is_not_a_required_check() -> None:
    # Setup
    probe = FakeProviderProbe(PASSING)

    # Execute
    check = DoctorCheck.optional("deno", probe)

    # Assert
    assert check == DoctorCheck("deno", False, probe)


def test_a_check_runs_its_probe_into_a_line_carrying_its_own_name_and_requirement() -> None:
    # Setup
    check = a_check("deno", False, FAILING)

    # Execute
    line = check.run()

    # Assert
    assert line == DoctorLine("deno", ok=False, required=False, detail="broken")


def test_a_check_whose_probe_raises_runs_into_a_failed_line_describing_the_error() -> None:
    # Setup
    check = a_check("database", True, RuntimeError("disk is on fire"))

    # Execute
    line = check.run()

    # Assert
    assert line == DoctorLine(
        "database", ok=False, required=True, detail="RuntimeError: disk is on fire"
    )
