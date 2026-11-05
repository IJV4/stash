from stash.hermes_adapter.callbacks import CallbackPress, PressHandler
from stash.hermes_adapter.outbox import LateBoundOutbox
from stash.hermes_adapter.telegram_io import TelegramApplication, TelegramAttachment


async def _unrouted(press: CallbackPress) -> None:
    raise RuntimeError("no registration is handling button presses yet")


class TelegramLink:
    def __init__(self) -> None:
        self._outbox = LateBoundOutbox()
        self._on_press: PressHandler = _unrouted
        self._attachment = TelegramAttachment(self._outbox, self._press)

    @property
    def outbox(self) -> LateBoundOutbox:
        return self._outbox

    def route_presses_to(self, on_press: PressHandler) -> None:
        self._on_press = on_press

    def on_connect(self, application: TelegramApplication, adapter: object) -> None:
        self._attachment.attach(application)

    async def _press(self, press: CallbackPress) -> None:
        await self._on_press(press)
