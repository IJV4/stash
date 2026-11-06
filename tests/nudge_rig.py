from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fakes.memory_store import MemoryStore
from fakes.scripted_sender import SendFailed
from nudge_builders import a_nudge_schedule

from stash.capture import Reply
from stash.capture.nudge_replies import nudge_reply
from stash.nudges import LOOKBACK, Nudger, Schedule, WeeklyDigest, batch_messages

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
AROUND = timedelta(minutes=10)


@dataclass(slots=True)
class NudgeRig:
    store: MemoryStore
    schedule: Schedule
    nudger: Nudger
    send: Callable[[Reply], None]
    sent: list[tuple[datetime, Reply]] = field(default_factory=list)

    def tick(self, now: datetime) -> None:
        for message in batch_messages(self.nudger.due(now), now):
            rendered = nudge_reply(message)
            try:
                self.send(rendered.reply)
            except SendFailed:
                continue
            self.sent.append((now, rendered.reply))
            self.nudger.mark_sent(rendered.shown, now)

    def tick_through(self, instants: Iterable[datetime]) -> None:
        for now in instants:
            self.tick(now)

    def sent_texts(self) -> list[tuple[datetime, str]]:
        return [(at, reply.text) for at, reply in self.sent]

    def digests_before_were_sent(self, first_tick: datetime) -> None:
        for instant in self.schedule.digest_instants_between(first_tick - LOOKBACK, first_tick):
            self.store.record_sent(WeeklyDigest(instant, ()).nudge, instant)


def sending_nowhere(reply: Reply) -> None:
    return None


def a_nudge_rig(
    store: MemoryStore | None = None, send: Callable[[Reply], None] = sending_nowhere
) -> NudgeRig:
    store = store or MemoryStore()
    schedule = a_nudge_schedule()
    return NudgeRig(store, schedule, Nudger(store, schedule), send)


def ticks_between(start: datetime, end: datetime, every: timedelta) -> list[datetime]:
    count = (end - start) // every
    return [start + every * n for n in range(count + 1)]


def hourly_ticks_with_minutes_around(
    start: datetime, end: datetime, busy: Sequence[datetime]
) -> list[datetime]:
    ticks = set(ticks_between(start, end, HOUR))
    for instant in busy:
        ticks.update(ticks_between(instant - AROUND, instant + AROUND, MINUTE))
    return sorted(ticks)
