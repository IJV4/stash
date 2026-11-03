import json
import sqlite3
from datetime import UTC, date, datetime

from stash.domain import CaptureStatus, Item, ItemType, RawCapture, SourceRef, Stage


def utc_text(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


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


def item_values(item: Item) -> tuple[str | None, ...]:
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
        None if item.date is None else item.date.isoformat(),
        utc_text(item.created_at),
        utc_text(item.updated_at),
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
        date=None if row["date"] is None else date.fromisoformat(row["date"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
