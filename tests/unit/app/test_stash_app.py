from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from app_builders import an_app
from fakes.chat_model import FakeChatModel
from fakes.close_counter import CloseCounter

from stash.config import ProviderName
from stash.evaluation import EvalTarget


def test_closing_the_app_closes_its_resources() -> None:
    # Setup
    resources = CloseCounter()
    app = an_app(resources=resources)

    # Execute
    app.close()

    # Assert
    assert resources.closes == 1


def test_the_app_cannot_be_modified() -> None:
    # Setup
    app = an_app()

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        app.ocr = None  # type: ignore[misc, assignment]


def test_the_eval_targets_cannot_be_modified() -> None:
    # Setup
    target = EvalTarget("local", FakeChatModel())
    app = an_app(eval_targets={ProviderName.OLLAMA: target})

    # Execute / Assert
    with pytest.raises(TypeError):
        app.eval_targets[ProviderName.OPENROUTER] = target  # type: ignore[index]


def test_the_eval_targets_do_not_change_when_the_source_mapping_does() -> None:
    # Setup
    source = {ProviderName.OLLAMA: EvalTarget("local", FakeChatModel())}
    app = an_app(eval_targets=source)

    # Execute
    source.clear()

    # Assert
    assert set(app.eval_targets) == {ProviderName.OLLAMA}


LATE_EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


def test_local_now_is_the_clock_in_the_configured_timezone() -> None:
    # Setup
    app = an_app(clock=lambda: LATE_EVENING_IN_LOS_ANGELES)

    # Execute
    now = app.local_now()

    # Assert
    assert (now, now.tzinfo) == (LATE_EVENING_IN_LOS_ANGELES, ZoneInfo("America/Los_Angeles"))


def test_today_is_the_calendar_day_in_the_configured_timezone() -> None:
    # Setup
    app = an_app(clock=lambda: LATE_EVENING_IN_LOS_ANGELES)

    # Execute
    today = app.today()

    # Assert
    assert today == date(2026, 11, 2)
