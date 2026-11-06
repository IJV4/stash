ALTER TABLE items ADD COLUMN cool_off_until TEXT;

CREATE TABLE steps (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    lead_days INTEGER,
    due_on TEXT,
    confirmed INTEGER NOT NULL,
    done INTEGER NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX steps_by_item ON steps (item_id);

CREATE TABLE sent_nudges (
    kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    due_at TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE (kind, subject_id, due_at)
);
