import logging
from collections.abc import Callable

from stash.hermes_adapter.callbacks import CallbackPress, PressHandler
from stash.hermes_adapter.outbox import LateBoundOutbox
from stash.hermes_adapter.telegram_io import TelegramApplication, TelegramAttachment

logger = logging.getLogger(__name__)

START_UP_FAILED_LOG = "the start-up callback failed; Telegram is still attached"


def _nothing() -> None:
    return None


async def _unrouted(press: CallbackPress) -> None:
    raise RuntimeError("no registration is handling button presses yet")


class TelegramLink:
    def __init__(self) -> None:
        self._outbox = LateBoundOutbox()
        self._on_press: PressHandler = _unrouted
        self._on_connected: Callable[[], None] = _nothing
        self._attachment = TelegramAttachment(self._outbox, self._press)

    @property
    def outbox(self) -> LateBoundOutbox:
        return self._outbox

    def route_presses_to(self, on_press: PressHandler) -> None:
        self._on_press = on_press

    def start_with(self, on_connected: Callable[[], None]) -> None:
        self._on_connected = on_connected

    def on_connect(self, application: TelegramApplication, adapter: object) -> None:
        self._attachment.attach(application)
        try:
            self._on_connected()
        except Exception:
            logger.exception(START_UP_FAILED_LOG)

    async def _press(self, press: CallbackPress) -> None:
        await self._on_press(press)
