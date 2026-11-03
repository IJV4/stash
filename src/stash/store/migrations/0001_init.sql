CREATE TABLE captures (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    text TEXT NOT NULL,
    media_paths TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE (chat_id, message_id)
);

CREATE TABLE items (
    id TEXT PRIMARY KEY,
    capture_id TEXT NOT NULL REFERENCES captures (id),
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    stage TEXT NOT NULL,
    source_url TEXT,
    note TEXT NOT NULL,
    details TEXT NOT NULL,
    tags TEXT NOT NULL,
    people TEXT NOT NULL,
    date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
