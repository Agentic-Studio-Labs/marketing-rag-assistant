from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    section_title TEXT,
    content_type TEXT,
    persona TEXT,
    funnel_stage TEXT,
    body TEXT NOT NULL,
    embedding BLOB,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_path);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def embedding_to_blob(vec: np.ndarray) -> bytes:
    v = vec.astype(np.float32).flatten()
    return v.tobytes()


def blob_to_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).reshape(-1)


def insert_chunk(
    conn: sqlite3.Connection,
    *,
    source_path: str,
    section_title: str | None,
    content_type: str | None,
    persona: str | None,
    funnel_stage: str | None,
    body: str,
    embedding: np.ndarray | None,
    commit: bool = True,
) -> int:
    blob = embedding_to_blob(embedding) if embedding is not None else None
    cur = conn.execute(
        """
        INSERT INTO chunks (
            source_path, section_title, content_type,
            persona, funnel_stage, body, embedding
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_path, section_title, content_type, persona, funnel_stage, body, blob),
    )
    if commit:
        conn.commit()
    return int(cur.lastrowid)


def clear_chunks(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunks")
    conn.commit()


def count_chunks(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()
    return int(row["c"]) if row else 0


def cosine_top_k(
    conn: sqlite3.Connection,
    query_vec: np.ndarray,
    k: int,
) -> list[tuple[int, float, sqlite3.Row]]:
    """Brute-force cosine similarity; swap for sqlite-vss at scale."""
    q = query_vec.astype(np.float32).flatten()
    qn = np.linalg.norm(q)
    if qn <= 0:
        return []
    q = q / qn

    rows = conn.execute(
        """
        SELECT id, body, source_path, section_title, content_type, persona,
               funnel_stage, embedding
        FROM chunks
        WHERE embedding IS NOT NULL
        """
    ).fetchall()

    scored: list[tuple[int, float, sqlite3.Row]] = []
    for row in rows:
        blob = row["embedding"]
        if not blob:
            continue
        v = blob_to_embedding(bytes(blob))
        vn = np.linalg.norm(v)
        if vn <= 0:
            continue
        v = v / vn
        score = float(np.dot(q, v))
        scored.append((int(row["id"]), score, row))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def log_event(
    conn: sqlite3.Connection,
    event_type: str,
    detail: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_log (event_type, detail) VALUES (?, ?)",
        (event_type, detail),
    )
    conn.commit()


def get_audit_log(
    conn: sqlite3.Connection,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, str | int | None]]:
    rows = conn.execute(
        """
        SELECT id, event_type, detail, created_at
        FROM audit_log
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "detail": r["detail"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def count_audit_log(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM audit_log").fetchone()
    return int(row["c"]) if row else 0
