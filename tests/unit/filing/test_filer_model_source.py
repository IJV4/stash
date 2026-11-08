import pytest
from fakes.chat_model import FakeChatModel
from fakes.model_source import FakeModelSource
from filing_rig import LOS_ANGELES, NOON_UTC

from stash.filing import Filer
from stash.llm import LlmDeferred, ModelSource


def a_filer(source: ModelSource) -> Filer:
    return Filer(source, lambda: NOON_UTC, LOS_ANGELES)


def test_a_deferral_from_the_source_propagates() -> None:
    # Setup
    deferred = LlmDeferred("busy")
    filer = a_filer(FakeModelSource(FakeChatModel(), error=deferred))

    # Execute / Assert
    with pytest.raises(LlmDeferred) as raised:
        filer.file("Miso soup", None)
    assert raised.value is deferred
