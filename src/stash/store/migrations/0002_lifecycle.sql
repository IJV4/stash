ALTER TABLE items ADD COLUMN kept INTEGER NOT NULL DEFAULT 0;

ALTER TABLE items ADD COLUMN parent_id TEXT REFERENCES items (id) ON DELETE SET NULL;

ALTER TABLE items ADD COLUMN drop_reason TEXT;

CREATE INDEX items_by_parent ON items (parent_id);

CREATE TABLE outcomes (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    completed_on TEXT NOT NULL,
    rating INTEGER,
    notes TEXT NOT NULL,
    takeaways TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    edited_at TEXT
);

CREATE INDEX outcomes_by_item ON outcomes (item_id);
