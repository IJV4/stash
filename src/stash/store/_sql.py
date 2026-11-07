INSERT_CAPTURE = """
INSERT INTO captures (id, chat_id, message_id, received_at, text, media_paths, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (chat_id, message_id) DO NOTHING
"""

UPSERT_ITEM = """
INSERT INTO items (id, capture_id, item_type, title, stage, source_url, note, details,
                   tags, people, date, created_at, updated_at, kept, parent_id, drop_reason,
                   cool_off_until)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    drop_reason = excluded.drop_reason,
    cool_off_until = excluded.cool_off_until
"""

UPDATE_ITEM = """
UPDATE items SET
    capture_id = ?2,
    item_type = ?3,
    title = ?4,
    stage = ?5,
    source_url = ?6,
    note = ?7,
    details = ?8,
    tags = ?9,
    people = ?10,
    date = ?11,
    created_at = ?12,
    updated_at = ?13,
    kept = ?14,
    parent_id = ?15,
    drop_reason = ?16,
    cool_off_until = ?17
WHERE id = ?1
"""

ITEM_BY_ID = "SELECT * FROM items WHERE id = ?"

ITEM_HOLDS_ITEMS = "SELECT 1 FROM items WHERE parent_id = ? LIMIT 1"

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

ITEMS_DATED_BETWEEN = """
SELECT * FROM items WHERE date BETWEEN :start AND :end ORDER BY date, created_at, id
"""

PLANNED_AWAITING_OUTCOME_DATED_BETWEEN = """
SELECT * FROM items
WHERE stage = :planned AND date BETWEEN :start AND :end
  AND NOT EXISTS (
    SELECT 1 FROM outcomes
    WHERE outcomes.item_id = items.id AND outcomes.completed_on = items.date
  )
ORDER BY date, created_at, id
"""

STAGE_OLDER_THAN = """
SELECT * FROM items WHERE stage = :stage AND updated_at < :cutoff
ORDER BY updated_at, id
LIMIT :limit
"""

CREATED_BETWEEN = """
SELECT * FROM items WHERE created_at >= :start AND created_at < :end
ORDER BY created_at DESC, id DESC
"""

DELETE_ITEM_IF_UNTOUCHED = """
DELETE FROM items
WHERE id = :item_id AND stage <> :done AND kept = 0
  AND NOT EXISTS (SELECT 1 FROM outcomes WHERE outcomes.item_id = items.id)
  AND NOT EXISTS (SELECT 1 FROM items AS child WHERE child.parent_id = items.id)
"""

UPSERT_STEP = """
INSERT INTO steps (id, item_id, text, lead_days, due_on, confirmed, done, position, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    text = excluded.text,
    lead_days = excluded.lead_days,
    due_on = excluded.due_on,
    confirmed = excluded.confirmed,
    done = excluded.done,
    position = excluded.position,
    created_at = excluded.created_at
WHERE steps.item_id = excluded.item_id
"""

DELETE_STEPS_OF_ITEM = "DELETE FROM steps WHERE item_id = ?"

STEPS_FOR_ITEM = "SELECT * FROM steps WHERE item_id = ? ORDER BY position, id"

STEP_BY_ID = "SELECT * FROM steps WHERE id = ?"

OPEN_CONFIRMED_STEPS = """
SELECT * FROM steps WHERE confirmed = 1 AND done = 0 ORDER BY item_id, position, id
"""

INSERT_SENT_NUDGE = """
INSERT INTO sent_nudges (kind, subject_id, due_at, sent_at) VALUES (?, ?, ?, ?)
ON CONFLICT (kind, subject_id, due_at) DO NOTHING
"""

NUDGE_WAS_SENT = "SELECT 1 FROM sent_nudges WHERE kind = ? AND subject_id = ? AND due_at = ?"

LAST_SENT = "SELECT max(sent_at) AS latest FROM sent_nudges WHERE kind = ?"

UPSERT_PERSON = """
INSERT INTO people (id, name, relation, aliases, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    name = excluded.name,
    relation = excluded.relation,
    aliases = excluded.aliases,
    notes = excluded.notes,
    created_at = excluded.created_at
"""

PERSON_BY_ID = "SELECT * FROM people WHERE id = ?"

PERSON_EXISTS = "SELECT 1 FROM people WHERE id = ?"

ALL_PEOPLE = "SELECT * FROM people ORDER BY casefold(name), id"

DELETE_PERSON = "DELETE FROM people WHERE id = ?"

UPSERT_KEY_DATE = """
INSERT INTO key_dates (id, person_id, kind, label, month, day, year) VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    person_id = excluded.person_id,
    kind = excluded.kind,
    label = excluded.label,
    month = excluded.month,
    day = excluded.day,
    year = excluded.year
"""

DELETE_KEY_DATE = "DELETE FROM key_dates WHERE id = ?"

KEY_DATES_FOR_PERSON = "SELECT * FROM key_dates WHERE person_id = ? ORDER BY month, day, id"

ALL_KEY_DATES = "SELECT * FROM key_dates"

LINK_ITEM_TO_PERSON = "INSERT OR IGNORE INTO item_people (item_id, person_id) VALUES (?, ?)"

UNLINK_ITEM_FROM_PERSON = "DELETE FROM item_people WHERE item_id = ? AND person_id = ?"

PEOPLE_FOR_ITEM = """
SELECT people.* FROM people
JOIN item_people ON item_people.person_id = people.id
WHERE item_people.item_id = ?
ORDER BY casefold(people.name), people.id
"""

ITEMS_FOR_PERSON = """
SELECT items.* FROM items
JOIN item_people ON item_people.item_id = items.id
WHERE item_people.person_id = :person_id
  AND (:item_type IS NULL OR items.item_type = :item_type)
ORDER BY items.created_at DESC, items.id DESC
"""
