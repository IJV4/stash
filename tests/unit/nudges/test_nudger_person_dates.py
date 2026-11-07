from datetime import date, datetime, timedelta

from builders import BASE, in_los_angeles
from fakes.memory_store import MemoryStore
from nudge_builders import a_nudger, only
from people_builders import (
    a_key_date,
    stored_ana_with_a_march_sixth_birthday,
    stored_gift_idea,
)

from stash.domain import ItemType, Stage
from stash.nudges import PersonDateReminder
from stash.store import Store

MARCH_SIXTH = date(2027, 3, 6)
UUID_HEX_ID = "0123456789abcdef0123456789abcdef"
FEBRUARY_TWENTIETH_MORNING = in_los_angeles(date(2027, 2, 20), 9)
MARCH_SIXTH_MORNING = in_los_angeles(MARCH_SIXTH, 9)


def person_dates(store: Store, now: datetime, **nudger: object) -> list[PersonDateReminder]:
    return only(PersonDateReminder, a_nudger(store, **nudger).due(now))


def on_the_day(reminders: list[PersonDateReminder]) -> list[PersonDateReminder]:
    return [reminder for reminder in reminders if reminder.lead == 0]


def test_a_february_29_birthday_is_reminded_on_february_28_in_a_common_year() -> None:
    # Setup
    store = MemoryStore()
    ana = stored_ana_with_a_march_sixth_birthday(store)
    store.save_key_date(a_key_date(id="leap", person_id=ana.id, month=2, day=29, year=2000))
    february_28 = in_los_angeles(date(2027, 2, 28), 9)

    # Execute
    reminders = on_the_day(person_dates(store, february_28))

    # Assert
    assert [reminder.on for reminder in reminders] == [date(2027, 2, 28)]


def test_the_subject_names_the_key_date_its_occurrence_and_the_lead() -> None:
    # Setup
    store = MemoryStore()
    ana = stored_ana_with_a_march_sixth_birthday(store)
    store.save_key_date(a_key_date(id=UUID_HEX_ID, person_id=ana.id, month=3, day=6))

    # Execute
    reminders = on_the_day(person_dates(store, MARCH_SIXTH_MORNING))

    # Assert
    assert UUID_HEX_ID + "@2027-03-06#0" in [reminder.nudge.subject_id for reminder in reminders]


def test_gift_ideas_are_the_linked_gift_items_that_are_not_done_or_dropped_newest_first() -> None:
    # Setup
    store = MemoryStore()
    ana = stored_ana_with_a_march_sixth_birthday(store)
    stored_gift_idea(store, ana, "Pottery wheel", created_at=BASE)
    stored_gift_idea(store, ana, "Ceramic class", created_at=BASE + timedelta(days=1))
    stored_gift_idea(store, ana, "Scarf", stage=Stage.DONE)
    stored_gift_idea(store, ana, "Mug", stage=Stage.DROPPED, drop_reason="gave up")
    stored_gift_idea(store, ana, "Novel", item_type=ItemType.BOOK)

    # Execute
    [reminder] = person_dates(store, FEBRUARY_TWENTIETH_MORNING)

    # Assert
    assert reminder.gift_ideas == ("Ceramic class", "Pottery wheel")


def test_only_the_configured_lead_days_get_a_reminder() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)
    one_week_before = in_los_angeles(date(2027, 2, 27), 9)

    # Execute
    reminders = person_dates(store, one_week_before, lead_days=(7,))

    # Assert
    assert [reminder.lead for reminder in reminders] == [7]
