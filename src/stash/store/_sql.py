INSERT_CAPTURE = """
INSERT INTO captures (id, chat_id, message_id, received_at, text, media_paths, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (chat_id, message_id) DO NOTHING
"""

UPSERT_ITEM = """
INSERT INTO items (id, capture_id, item_type, title, stage, source_url, note, details,
                   tags, people, date, created_at, updated_at, kept, parent_id, drop_reason)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    capture_id = excluded.capture_id,
    item_type = excluded.item_type,
    title = excluded.title,
    stage = excluded.stage,
    source_url = excluded.source_url,
    note = excluded.note,
    details = excluded.details,
    tags = excluded.tags,
    people = excluded.people,
    date = excluded.date,
    created_at = excluded.created_at,
    updated_at = excluded.updated_at,
    kept = excluded.kept,
    parent_id = excluded.parent_id,
    drop_reason = excluded.drop_reason
"""

LIST_ITEMS = """
SELECT * FROM items
WHERE (:stage IS NULL OR stage = :stage) AND (:item_type IS NULL OR item_type = :item_type)
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset
"""

SEARCH_ITEMS = """
SELECT * FROM items
WHERE instr(casefold(title), :needle) > 0
   OR instr(casefold(note), :needle) > 0
   OR EXISTS (SELECT 1 FROM json_each(items.tags) WHERE instr(casefold(value), :needle) > 0)
ORDER BY created_at DESC, id DESC
LIMIT :limit
"""

UPSERT_SETTING = """
INSERT INTO settings (key, value) VALUES (?, ?)
ON CONFLICT (key) DO UPDATE SET value = excluded.value
"""

INSERT_OUTCOME = """
INSERT INTO outcomes (id, item_id, completed_on, rating, notes, takeaways, recorded_at, edited_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

UPSERT_OUTCOME = (
    INSERT_OUTCOME
    + """
ON CONFLICT (id) DO UPDATE SET
    item_id = excluded.item_id,
    completed_on = excluded.completed_on,
    rating = excluded.rating,
    notes = excluded.notes,
    takeaways = excluded.takeaways,
    recorded_at = excluded.recorded_at,
    edited_at = excluded.edited_at
"""
)

OUTCOMES_FOR_ITEM = """
SELECT * FROM outcomes WHERE item_id = ? ORDER BY completed_on, recorded_at, id
"""

OUTCOME_BY_ID = "SELECT * FROM outcomes WHERE id = ?"

ITEM_EXISTS = "SELECT 1 FROM items WHERE id = ?"

CAPTURE_EXISTS = "SELECT 1 FROM captures WHERE id = ?"

LIBRARY = """
WITH latest AS (
    SELECT item_id, completed_on, recorded_at, id AS outcome_id,
           row_number() OVER (
               PARTITION BY item_id ORDER BY completed_on DESC, recorded_at DESC, id DESC
           ) AS recency
    FROM outcomes
)
SELECT items.* FROM items
LEFT JOIN latest ON latest.item_id = items.id AND latest.recency = 1
WHERE items.kept = 1 AND items.stage != :dropped
  AND (:item_type IS NULL OR items.item_type = :item_type)
ORDER BY latest.item_id IS NULL, latest.completed_on DESC, latest.recorded_at DESC,
         latest.outcome_id DESC, items.created_at DESC, items.id DESC
LIMIT :limit OFFSET :offset
"""

CHILDREN_OF = """
SELECT * FROM items WHERE parent_id = ? ORDER BY created_at, id
"""

DONE_BETWEEN = """
WITH in_range AS (
    SELECT item_id, completed_on, recorded_at,
           row_number() OVER (
               PARTITION BY item_id ORDER BY completed_on DESC, recorded_at DESC, id DESC
           ) AS recency
    FROM outcomes
    WHERE completed_on BETWEEN :start AND :end
)
SELECT items.* FROM items
JOIN in_range ON in_range.item_id = items.id AND in_range.recency = 1
ORDER BY in_range.completed_on DESC, in_range.recorded_at DESC, items.id DESC
"""

DELETE_ITEM_IF_UNTOUCHED = """
DELETE FROM items
WHERE id = :item_id AND stage <> :done AND kept = 0
  AND NOT EXISTS (SELECT 1 FROM outcomes WHERE outcomes.item_id = items.id)
  AND NOT EXISTS (SELECT 1 FROM items AS child WHERE child.parent_id = items.id)
"""
