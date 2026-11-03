import pytest
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from filing_rig import LOS_ANGELES, NOON_UTC

from stash.config import LlmTask
from stash.domain import ItemType
from stash.filing import Filer, FilingModelSource
from stash.llm import LlmDeferred


def a_filer(source: FilingModelSource) -> Filer:
    return Filer(source, lambda: NOON_UTC, LOS_ANGELES)


def test_a_filer_files_with_the_model_its_source_provides() -> None:
    # Setup
    source = FakeModelSource(FakeChatModel(reply={"item_type": "recipe"}))

    # Execute
    filing = a_filer(source).file("Miso soup", None)

    # Assert
    assert filing.item_type is ItemType.RECIPE


def test_a_filer_asks_its_source_for_the_filing_task_at_the_clock_time() -> None:
    # Setup
    source = FakeModelSource(FakeChatModel())

    # Execute
    a_filer(source).file("Miso soup", None)

    # Assert
    assert source.requests == [(LlmTask.FILING, NOON_UTC)]


def test_a_filer_does_not_ask_its_source_when_there_is_nothing_to_file() -> None:
    # Setup
    source = FakeModelSource(FakeChatModel())

    # Execute
    a_filer(source).file("", None)

    # Assert
    assert source.requests == []


def test_a_deferral_from_the_source_propagates() -> None:
    # Setup
    deferred = LlmDeferred("busy")
    filer = a_filer(FakeModelSource(FakeChatModel(), error=deferred))

    # Execute / Assert
    with pytest.raises(LlmDeferred) as raised:
        filer.file("Miso soup", None)
    assert raised.value is deferred
