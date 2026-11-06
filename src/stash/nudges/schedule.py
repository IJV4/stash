import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from stash.config.nudges import NudgeConfig

_ONE_DAY = dt.timedelta(days=1)


@dataclass(frozen=True, slots=True)
class Schedule:
    config: NudgeConfig
    timezone: ZoneInfo

    def at_local(self, day: dt.date, at: dt.time) -> dt.datetime:
        return dt.datetime.combine(day, at, tzinfo=self.timezone).astimezone(dt.UTC)

    def local_date(self, instant: dt.datetime) -> dt.date:
        return instant.astimezone(self.timezone).date()

    def reminder_at(self, day: dt.date) -> dt.datetime:
        return self.at_local(day, self.config.reminder_time)

    def followup_at(self, item_date: dt.date) -> dt.datetime:
        return self.at_local(item_date + _ONE_DAY, self.config.followup_time)

    def item_dates_followed_up_between(
        self, first: dt.date, last: dt.date
    ) -> tuple[dt.date, dt.date]:
        return first - _ONE_DAY, last - _ONE_DAY

    def latest_followup_slot(self, now: dt.datetime) -> dt.datetime:
        today = self.at_local(self.local_date(now), self.config.followup_time)
        if today <= now:
            return today
        return self.at_local(self.local_date(now) - _ONE_DAY, self.config.followup_time)

    def stuck_cutoff(self, at: dt.datetime) -> dt.datetime:
        return at - dt.timedelta(days=self.config.stuck_doing_days)

    def digest_instants_between(self, start: dt.datetime, end: dt.datetime) -> list[dt.datetime]:
        first, last = self.local_date(start), self.local_date(end)
        days = (first + dt.timedelta(days=offset) for offset in range((last - first).days + 1))
        instants = (
            self.at_local(day, self.config.digest_time)
            for day in days
            if day.weekday() == self.config.digest_day.python_weekday
        )
        return [instant for instant in instants if start <= instant <= end]

    def latest_digest_between(self, start: dt.datetime, end: dt.datetime) -> dt.datetime | None:
        instants = self.digest_instants_between(start, end)
        return instants[-1] if instants else None
