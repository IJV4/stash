import asyncio
from dataclasses import dataclass
from typing import Any

from app_builders import an_app
from builders import stored
from fakes.fake_telegram_bot import FakeTelegramApplication, FakeTelegramBot
from fakes.ptb_callback_updates import AnsweringBot, callback_update
from fakes.recording_assistant import RecordingAssistant
from fakes.store_factories import FreshStore
from hermes_events import OWNER_ID
from nudge_builders import FRIDAY, SATURDAY, SUNDAY_MORNING, a_planned_date_night
from nudge_rig import a_nudge_rig

from stash.capture import Reply
from stash.hermes_adapter.outbox import LateBoundOutbox
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.telegram_io import TelegramAttachment, to_keyboard
from stash.hermes_adapter.wiring import build_callbacks

PRESSED_MESSAGE_ID = 55


@dataclass(frozen=True, slots=True)
class TelegramPressRig:
    application: FakeTelegramApplication

    @property
    def bot(self) -> FakeTelegramBot:
        return self.application.bot

    def sent_headlines(self) -> list[str]:
        return [sent.text.splitlines()[0] for sent in self.bot.sent]

    def press(self, on: Reply, data: str) -> None:
        handler: Any = self.application.handlers[0]
        update = callback_update(
            AnsweringBot([]),
            data=data,
            chat_id=int(OWNER_ID),
            user_id=int(OWNER_ID),
            message_id=PRESSED_MESSAGE_ID,
            keyboard=to_keyboard(on),
        )
        asyncio.run(handler.callback(update, None))


def a_telegram_press_rig(store: FreshStore) -> TelegramPressRig:
    outbox = LateBoundOutbox()
    callbacks = build_callbacks(
        an_app(store=store), Owners.parse(OWNER_ID), outbox, RecordingAssistant()
    )
    application = FakeTelegramApplication()
    TelegramAttachment(outbox, callbacks.on_press).attach(application)
    return TelegramPressRig(application)


def two_follow_ups_in_one_message(store: FreshStore) -> Reply:
    stored(store, a_planned_date_night(id="first", title="First", date=FRIDAY))
    stored(store, a_planned_date_night(id="second", title="Second", date=SATURDAY))
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SUNDAY_MORNING)
    rig.tick(SUNDAY_MORNING)
    return rig.sent[-1][1]
