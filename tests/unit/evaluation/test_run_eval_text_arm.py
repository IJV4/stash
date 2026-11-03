from datetime import UTC, datetime

import pytest
from eval_builders import a_text_case, an_expectation, an_image_case
from eval_rig import LOS_ANGELES, NOON_UTC, UTC_ZONE, an_answer, run_cases
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr
from fakes.timer import StepTimer
from filing_rig import sent_texts
from link_builders import a_link_info

from stash.domain import ItemType, Route, Stage
from stash.evaluation import EvalArm, EvalField, EvalTarget, run_eval


def test_a_filing_of_the_expected_type_passes_the_item_type_field() -> None:
    # Setup
    case = a_text_case(expect=an_expectation(item_type=ItemType.PLACE))
    model = FakeChatModel(an_answer(item_type="place"))

    # Execute
    result = run_cases([case], model).results[0]

    # Assert
    assert EvalField.ITEM_TYPE in result.passed_fields


def test_a_filing_in_the_wrong_stage_fails_the_stage_field() -> None:
    # Setup
    case = a_text_case(expect=an_expectation(stage=Stage.PLANNED))
    model = FakeChatModel(an_answer(stage="want_to"))

    # Execute
    result = run_cases([case], model).results[0]

    # Assert
    assert EvalField.STAGE in result.failed_fields


def test_a_judged_case_reports_no_error() -> None:
    # Execute
    result = run_cases([a_text_case()]).results[0]

    # Assert
    assert result.error is None


def test_a_result_names_its_case_and_arm() -> None:
    # Execute
    result = run_cases([a_text_case(id="t07")]).results[0]

    # Assert
    assert (result.case_id, result.arm) == ("t07", EvalArm.TEXT)


def test_the_text_arm_sends_the_case_text_to_the_model() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases([a_text_case(text="Pastéis de Belém in Lisbon")], model)

    # Assert
    assert "<captured>\nPastéis de Belém in Lisbon\n</captured>" in sent_texts(model)[1]


def test_the_text_arm_sends_the_case_link_to_the_model() -> None:
    # Setup
    model = FakeChatModel(an_answer())
    case = a_text_case(link=a_link_info(title="Miso soup in five minutes"))

    # Execute
    run_cases([case], model)

    # Assert
    assert "Miso soup in five minutes" in sent_texts(model)[1]


def test_a_routing_case_passes_when_the_filing_takes_the_expected_route() -> None:
    # Setup
    case = a_text_case(text="what can I do?", expect=an_expectation(route=Route.REQUEST))
    model = FakeChatModel(an_answer(route="request"))

    # Execute
    result = run_cases([case], model).results[0]

    # Assert
    assert result.passed_fields == {EvalField.ROUTE}


def test_the_text_arm_skips_image_cases() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run = run_cases([an_image_case()], model)

    # Assert
    assert run.results == ()


def test_the_latency_of_a_case_is_the_time_it_took_to_file() -> None:
    # Execute
    result = run_cases([a_text_case()], timer=StepTimer(0.5)).results[0]

    # Assert
    assert result.latency_s == 0.5


def test_every_case_is_timed_separately() -> None:
    # Setup
    cases = [a_text_case(id="a"), a_text_case(id="b")]

    # Execute
    run = run_cases(cases, timer=StepTimer(0.25))

    # Assert
    assert [result.latency_s for result in run.results] == [0.25, 0.25]


def test_the_run_carries_the_label_of_its_target() -> None:
    # Execute
    run = run_cases([a_text_case()])

    # Assert
    assert run.label == "local"


def test_the_filer_resolves_today_in_the_given_timezone() -> None:
    # Setup
    model = FakeChatModel(an_answer())
    after_utc_midnight = datetime(2026, 11, 3, 2, 0, tzinfo=UTC)

    # Execute
    run_cases([a_text_case()], model, clock=lambda: after_utc_midnight, timezone=LOS_ANGELES)

    # Assert
    assert "Today is Monday 2026-11-02." in sent_texts(model)[1]


def test_the_filer_resolves_today_in_utc_when_given_the_utc_timezone() -> None:
    # Setup
    model = FakeChatModel(an_answer())

    # Execute
    run_cases(
        [a_text_case()],
        model,
        clock=lambda: datetime(2026, 11, 3, 2, 0, tzinfo=UTC),
        timezone=UTC_ZONE,
    )

    # Assert
    assert "Today is Tuesday 2026-11-03." in sent_texts(model)[1]


def test_no_arms_produce_no_results() -> None:
    # Execute
    run = run_cases([a_text_case()], arms=())

    # Assert
    assert run.results == ()


def test_naming_an_arm_twice_runs_it_once() -> None:
    # Execute
    run = run_cases([a_text_case()], arms=(EvalArm.TEXT, EvalArm.TEXT))

    # Assert
    assert len(run.results) == 1


def test_running_an_evaluation_without_a_timezone_is_refused() -> None:
    # Setup
    target = EvalTarget("local", FakeChatModel(an_answer()))

    # Execute / Assert
    with pytest.raises(TypeError, match="timezone"):
        run_eval([a_text_case()], target, [EvalArm.TEXT], FakeOcr(), lambda: NOON_UTC)
