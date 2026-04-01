from __future__ import annotations

import sqlite3

from config import CORPUS_DIR
from db import clear_chunks, count_chunks, init_schema, insert_chunk
from embed import embed_texts
from ingest import iter_corpus_files, load_chunks


def ensure_indexed(conn: sqlite3.Connection) -> None:
    init_schema(conn)
    if count_chunks(conn) > 0:
        return

    files = iter_corpus_files(CORPUS_DIR)
    if not files:
        return

    rows: list[dict[str, str | None]] = []
    for path in files:
        for chunk in load_chunks(path, CORPUS_DIR):
            rows.append(chunk)

    bodies = [str(r["body"]) for r in rows]
    vectors = embed_texts(bodies)

    for row, vec in zip(rows, vectors, strict=True):
        insert_chunk(
            conn,
            source_path=str(row["source_path"]),
            section_title=row["section_title"] if row["section_title"] else None,
            content_type=row.get("content_type")
            if isinstance(row.get("content_type"), str)
            else None,
            persona=row.get("persona") if isinstance(row.get("persona"), str) else None,
            funnel_stage=row.get("funnel_stage")
            if isinstance(row.get("funnel_stage"), str)
            else None,
            body=str(row["body"]),
            embedding=vec,
            commit=False,
        )
    conn.commit()


def reindex_corpus(conn: sqlite3.Connection) -> None:
    init_schema(conn)
    clear_chunks(conn)
    ensure_indexed(conn)
