CREATE TABLE people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relation TEXT NOT NULL,
    aliases TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE key_dates (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    year INTEGER
);

CREATE INDEX key_dates_by_person ON key_dates (person_id);

CREATE TABLE item_people (
    item_id TEXT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    PRIMARY KEY (item_id, person_id)
);

CREATE INDEX item_people_by_person ON item_people (person_id);
