from collections.abc import Callable
from datetime import datetime

from builders import BASE, LOS_ANGELES
from fakes.model_source import FakeModelSource

from stash.llm import ChatModel
from stash.suggestions import SuggestionEngine


def an_engine(model: ChatModel, clock: Callable[[], datetime] = lambda: BASE) -> SuggestionEngine:
    return SuggestionEngine(FakeModelSource(model), clock, LOS_ANGELES)
