import json
import sqlite3
from datetime import date, datetime

from stash.domain import (
    CaptureStatus,
    Item,
    ItemType,
    KeyDate,
    KeyDateKind,
    Outcome,
    Person,
    RawCapture,
    SourceRef,
    Stage,
    Step,
    utc_text,
)


def capture_values(capture: RawCapture) -> tuple[str, ...]:
    return (
        capture.id,
        capture.source.chat_id,
        capture.source.message_id,
        utc_text(capture.received_at),
        capture.text,
        _json(capture.media_paths),
        capture.status.value,
    )


def capture_from_row(row: sqlite3.Row) -> RawCapture:
    return RawCapture(
        id=row["id"],
        source=SourceRef(chat_id=row["chat_id"], message_id=row["message_id"]),
        received_at=datetime.fromisoformat(row["received_at"]),
        text=row["text"],
        media_paths=tuple(json.loads(row["media_paths"])),
        status=CaptureStatus(row["status"]),
    )


def item_values(item: Item) -> tuple[str | int | None, ...]:
    return (
        item.id,
        item.capture_id,
        item.item_type.value,
        item.title,
        item.stage.value,
        item.source_url,
        item.note,
        _json(dict(item.details)),
        _json(item.tags),
        _json(item.people),
        optional_date_text(item.date),
        utc_text(item.created_at),
        utc_text(item.updated_at),
        int(item.kept),
        item.parent_id,
        item.drop_reason,
        optional_date_text(item.cool_off_until),
    )


def item_from_row(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"],
        capture_id=row["capture_id"],
        item_type=ItemType(row["item_type"]),
        title=row["title"],
        stage=Stage(row["stage"]),
        source_url=row["source_url"],
        note=row["note"],
        details=json.loads(row["details"]),
        tags=tuple(json.loads(row["tags"])),
        people=tuple(json.loads(row["people"])),
        date=optional_date_from(row["date"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        kept=bool(row["kept"]),
        parent_id=row["parent_id"],
        drop_reason=row["drop_reason"],
        cool_off_until=optional_date_from(row["cool_off_until"]),
    )


def outcome_values(outcome: Outcome) -> tuple[str | int | None, ...]:
    return (
        outcome.id,
        outcome.item_id,
        outcome.completed_on.isoformat(),
        outcome.rating,
        outcome.notes,
        _json(outcome.takeaways),
        utc_text(outcome.recorded_at),
        None if outcome.edited_at is None else utc_text(outcome.edited_at),
    )


def outcome_from_row(row: sqlite3.Row) -> Outcome:
    return Outcome(
        id=row["id"],
        item_id=row["item_id"],
        completed_on=date.fromisoformat(row["completed_on"]),
        rating=row["rating"],
        notes=row["notes"],
        takeaways=tuple(json.loads(row["takeaways"])),
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        edited_at=None if row["edited_at"] is None else datetime.fromisoformat(row["edited_at"]),
    )


def step_values(step: Step) -> tuple[str | int | None, ...]:
    return (
        step.id,
        step.item_id,
        step.text,
        step.lead_days,
        optional_date_text(step.due_on),
        int(step.confirmed),
        int(step.done),
        step.position,
        utc_text(step.created_at),
    )


def step_from_row(row: sqlite3.Row) -> Step:
    return Step(
        id=row["id"],
        item_id=row["item_id"],
        text=row["text"],
        lead_days=row["lead_days"],
        due_on=optional_date_from(row["due_on"]),
        confirmed=bool(row["confirmed"]),
        done=bool(row["done"]),
        position=row["position"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def person_values(person: Person) -> tuple[str, ...]:
    return (
        person.id,
        person.name,
        person.relation,
        _json(person.aliases),
        person.notes,
        utc_text(person.created_at),
    )


def person_from_row(row: sqlite3.Row) -> Person:
    return Person(
        id=row["id"],
        name=row["name"],
        relation=row["relation"],
        aliases=tuple(json.loads(row["aliases"])),
        notes=row["notes"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def key_date_values(key_date: KeyDate) -> tuple[str | int | None, ...]:
    return (
        key_date.id,
        key_date.person_id,
        key_date.kind.value,
        key_date.label,
        key_date.month,
        key_date.day,
        key_date.year,
    )


def key_date_from_row(row: sqlite3.Row) -> KeyDate:
    return KeyDate(
        id=row["id"],
        person_id=row["person_id"],
        kind=KeyDateKind(row["kind"]),
        label=row["label"],
        month=row["month"],
        day=row["day"],
        year=row["year"],
    )


def optional_date_text(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def optional_date_from(text: str | None) -> date | None:
    return None if text is None else date.fromisoformat(text)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
