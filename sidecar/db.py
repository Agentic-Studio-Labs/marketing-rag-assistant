import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS marketing_content (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            summary TEXT DEFAULT '',
            content_type TEXT DEFAULT '',
            persona TEXT DEFAULT 'general',
            funnel_stage TEXT DEFAULT 'awareness',
            channel TEXT DEFAULT '',
            topics TEXT DEFAULT '[]',
            performance_score REAL DEFAULT 50,
            url TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            source_path TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS generated_content (
            id TEXT PRIMARY KEY,
            source_content_id TEXT NOT NULL REFERENCES marketing_content(id),
            source_title TEXT NOT NULL,
            format TEXT NOT NULL,
            tone TEXT NOT NULL,
            body TEXT NOT NULL,
            quality_score REAL,
            prompts TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_content_type ON marketing_content(content_type);
        CREATE INDEX IF NOT EXISTS idx_content_persona ON marketing_content(persona);
        CREATE INDEX IF NOT EXISTS idx_content_funnel ON marketing_content(funnel_stage);
        CREATE INDEX IF NOT EXISTS idx_gen_source ON generated_content(source_content_id);
        CREATE INDEX IF NOT EXISTS idx_gen_format ON generated_content(format);

        CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
            title, summary, body,
            content='marketing_content',
            content_rowid='rowid'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS generated_fts USING fts5(
            body,
            content='generated_content',
            content_rowid='rowid'
        );

        -- Triggers to keep FTS5 in sync with marketing_content
        CREATE TRIGGER IF NOT EXISTS content_ai AFTER INSERT ON marketing_content BEGIN
            INSERT INTO content_fts(rowid, title, summary, body)
            VALUES (new.rowid, new.title, new.summary, new.body);
        END;

        CREATE TRIGGER IF NOT EXISTS content_ad AFTER DELETE ON marketing_content BEGIN
            INSERT INTO content_fts(content_fts, rowid, title, summary, body)
            VALUES ('delete', old.rowid, old.title, old.summary, old.body);
        END;

        CREATE TRIGGER IF NOT EXISTS content_au AFTER UPDATE ON marketing_content BEGIN
            INSERT INTO content_fts(content_fts, rowid, title, summary, body)
            VALUES ('delete', old.rowid, old.title, old.summary, old.body);
            INSERT INTO content_fts(rowid, title, summary, body)
            VALUES (new.rowid, new.title, new.summary, new.body);
        END;

        -- Triggers for generated_content FTS
        CREATE TRIGGER IF NOT EXISTS gen_ai AFTER INSERT ON generated_content BEGIN
            INSERT INTO generated_fts(rowid, body) VALUES (new.rowid, new.body);
        END;

        CREATE TRIGGER IF NOT EXISTS gen_ad AFTER DELETE ON generated_content BEGIN
            INSERT INTO generated_fts(generated_fts, rowid, body)
            VALUES ('delete', old.rowid, old.body);
        END;

        CREATE TRIGGER IF NOT EXISTS gen_au AFTER UPDATE ON generated_content BEGIN
            INSERT INTO generated_fts(generated_fts, rowid, body)
            VALUES ('delete', old.rowid, old.body);
            INSERT INTO generated_fts(rowid, body) VALUES (new.rowid, new.body);
        END;

        -- Settings table for app config
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)


def insert_content(conn: sqlite3.Connection, content: dict) -> str:
    conn.execute(
        """INSERT OR REPLACE INTO marketing_content
        (id, title, body, summary, content_type, persona, funnel_stage,
         channel, topics, performance_score, url, created_at, source_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            content["id"],
            content["title"],
            content["body"],
            content.get("summary", ""),
            content.get("content_type", ""),
            content.get("persona", "general"),
            content.get("funnel_stage", "awareness"),
            content.get("channel", ""),
            content.get("topics", "[]"),
            content.get("performance_score", 50),
            content.get("url", ""),
            content.get("created_at", ""),
            content.get("source_path", ""),
        ),
    )
    conn.commit()
    return content["id"]


def get_content_by_id(conn: sqlite3.Connection, content_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM marketing_content WHERE id = ?", (content_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)
