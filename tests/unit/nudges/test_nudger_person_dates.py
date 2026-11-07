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


def test_a_birthday_five_days_ahead_gets_the_fourteen_day_lead_once_with_five_days_left() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)
    five_days_before = in_los_angeles(date(2027, 3, 1), 9)

    # Execute
    reminders = person_dates(store, five_days_before)

    # Assert
    assert [(reminder.lead, reminder.days_left) for reminder in reminders] == [(14, 5)]


def test_a_birthday_tomorrow_gets_the_two_day_lead_alone_with_one_day_left() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)
    the_day_before = in_los_angeles(date(2027, 3, 5), 9)

    # Execute
    reminders = person_dates(store, the_day_before)

    # Assert
    assert [(reminder.lead, reminder.days_left) for reminder in reminders] == [(2, 1)]


def test_a_birthday_reached_with_the_pc_off_since_the_two_day_lead_gets_one_reminder() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)

    # Execute
    reminders = person_dates(store, in_los_angeles(MARCH_SIXTH, 12))

    # Assert
    assert [(reminder.lead, reminder.days_left) for reminder in reminders] == [(0, 0)]


def test_a_birthday_that_has_already_passed_gets_no_reminder() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)

    # Execute
    reminders = person_dates(store, in_los_angeles(date(2027, 3, 7), 12))

    # Assert
    assert reminders == []


def test_a_december_30_birthday_is_first_reminded_fourteen_days_ahead_on_december_16() -> None:
    # Setup
    store = MemoryStore()
    ana = stored_ana_with_a_march_sixth_birthday(store)
    store.save_key_date(a_key_date(id="winter", person_id=ana.id, month=12, day=30, year=1990))
    december_mornings = [in_los_angeles(date(2027, 12, day), 9) for day in (15, 16)]

    # Execute
    reminded = [len(person_dates(store, morning, lead_days=(14,))) for morning in december_mornings]

    # Assert
    assert reminded == [0, 1]


def test_nothing_is_due_on_the_day_before_the_reminder_time_even_with_an_earlier_lead_unsent() -> (
    None
):
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)

    # Execute
    reminders = person_dates(store, in_los_angeles(MARCH_SIXTH, 7))

    # Assert
    assert reminders == []


def test_on_the_day_at_the_reminder_time_only_the_day_of_lead_is_due() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)

    # Execute
    reminders = person_dates(store, MARCH_SIXTH_MORNING)

    # Assert
    assert [(reminder.lead, reminder.days_left) for reminder in reminders] == [(0, 0)]
