from datetime import UTC, datetime

import pytest
from eval_builders import a_named_model, a_target, a_text_case, an_expectation
from eval_rig import LOS_ANGELES, NOON_UTC, UTC_ZONE, an_answer, read_fake_image
from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr
from filing_rig import sent_texts

from stash.config import ProviderName
from stash.domain import ItemType
from stash.evaluation import EvalArm, EvalField, evaluate


def test_evaluating_several_targets_gives_one_run_per_target_in_order() -> None:
    # Setup
    targets = [
        a_target(ProviderName.OLLAMA, text=a_named_model("local")),
        a_target(ProviderName.OPENROUTER, text=a_named_model("reference")),
    ]

    # Execute
    runs = evaluate(
        [a_text_case()],
        targets,
        [EvalArm.TEXT],
        FakeOcr(),
        lambda: NOON_UTC,
        timezone=UTC_ZONE,
    )

    # Assert
    assert [run.label for run in runs] == [
        "ollama:local thinking=default",
        "openrouter:reference thinking=default",
    ]


def test_each_target_is_judged_on_its_own_model() -> None:
    # Setup
    case = a_text_case(expect=an_expectation(item_type=ItemType.RECIPE))
    targets = [
        a_target(text=a_named_model(chat=FakeChatModel(an_answer(item_type="place")))),
        a_target(text=a_named_model(chat=FakeChatModel(an_answer(item_type="recipe")))),
    ]

    # Execute
    runs = evaluate([case], targets, [EvalArm.TEXT], FakeOcr(), lambda: NOON_UTC, timezone=UTC_ZONE)

    # Assert
    assert [EvalField.ITEM_TYPE in run.results[0].passed_fields for run in runs] == [False, True]


def test_evaluating_without_targets_gives_no_runs() -> None:
    # Execute
    runs = evaluate(
        [a_text_case()],
        [],
        [EvalArm.TEXT],
        FakeOcr(),
        lambda: NOON_UTC,
        read_image=read_fake_image,
        timezone=UTC_ZONE,
    )

    # Assert
    assert runs == []


def test_every_target_is_run_in_the_given_timezone() -> None:
    # Setup
    model = FakeChatModel(an_answer())
    after_utc_midnight = datetime(2026, 11, 3, 2, 0, tzinfo=UTC)

    # Execute
    evaluate(
        [a_text_case()],
        [a_target(text=a_named_model(chat=model))],
        [EvalArm.TEXT],
        FakeOcr(),
        lambda: after_utc_midnight,
        timezone=LOS_ANGELES,
    )

    # Assert
    assert "Today is Monday 2026-11-02." in sent_texts(model)[1]


def test_evaluating_without_a_timezone_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="timezone"):
        evaluate([a_text_case()], [], [EvalArm.TEXT], FakeOcr(), lambda: NOON_UTC)
