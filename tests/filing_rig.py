from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from config_builders import an_llm_config
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel

from stash.config import ProviderName
from stash.filing import Filer
from stash.llm import BusyCheck, ModelRouter, TextPart

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
NOON_UTC = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def build_filer(
    model: FakeChatModel,
    busy: BusyCheck | None = None,
    clock: Callable[[], datetime] | None = None,
) -> Filer:
    router = ModelRouter(
        an_llm_config(),
        {ProviderName.OLLAMA: model},
        FakeBusy() if busy is None else busy,
    )
    return Filer(router, (lambda: NOON_UTC) if clock is None else clock, LOS_ANGELES)


def sent_texts(model: FakeChatModel) -> list[str]:
    return [
        part.text
        for message in model.calls[0]
        for part in message.parts
        if isinstance(part, TextPart)
    ]
