import datetime as dt
import logging
from collections.abc import Callable

from stash.capture import Reply
from stash.capture.nudge_replies import nudge_reply
from stash.nudges import DigestBuilder, DueNudge, NudgeMessage, Nudger, WeeklyDigest, batch_messages

logger = logging.getLogger(__name__)

SEND_FAILED_LOG = "nudge send failed (%s); left unsent for the next tick"
MARK_SENT_FAILED_LOG = "nudge was sent but not recorded (%s); it may be sent again next tick"
ALREADY_RECORDED_LOG = "nudge message was already recorded by another sender; not sending it again"


class NudgeDelivery:
    def __init__(self, nudger: Nudger, digests: DigestBuilder) -> None:
        self._nudger = nudger
        self._digests = digests

    def deliver(self, now: dt.datetime, send: Callable[[Reply], None]) -> None:
        first_run = self._nudger.is_first_run()
        messages = self._messages(now)
        if first_run:
            self._record_without_sending(messages, now)
            return
        for message in messages:
            self._send(message, now, send)

    def preview(self, now: dt.datetime) -> tuple[Reply, ...]:
        if self._nudger.is_first_run():
            return ()
        return tuple(nudge_reply(message).reply for message in self._messages(now))

    def _messages(self, now: dt.datetime) -> tuple[NudgeMessage, ...]:
        due = [self._built(nudge, now) for nudge in self._nudger.due(now)]
        return batch_messages(due, now)

    def _built(self, due: DueNudge, now: dt.datetime) -> DueNudge:
        return self._digests.build(due, now) if isinstance(due, WeeklyDigest) else due

    def _record_without_sending(self, messages: tuple[NudgeMessage, ...], now: dt.datetime) -> None:
        everything = tuple(due for message in messages for due in message.due)
        if everything:
            self._nudger.mark_sent(NudgeMessage(everything, catch_up=False), now)

    def _send(self, message: NudgeMessage, now: dt.datetime, send: Callable[[Reply], None]) -> None:
        rendered = nudge_reply(message)
        try:
            send(rendered.reply)
        except Exception as error:
            logger.warning(SEND_FAILED_LOG, type(error).__name__)
            return
        self._record(rendered.shown, now)

    def _record(self, message: NudgeMessage, now: dt.datetime) -> None:
        try:
            recorded = self._nudger.mark_sent(message, now)
        except Exception as error:
            logger.warning(MARK_SENT_FAILED_LOG, type(error).__name__)
            return
        if not recorded:
            logger.warning(ALREADY_RECORDED_LOG)
