from __future__ import annotations

import numpy as np

from db import (
    connect,
    cosine_top_k,
    count_chunks,
    init_schema,
    insert_chunk,
)


def test_insert_and_retrieve(tmp_path) -> None:
    conn = connect(tmp_path / "test.db")
    init_schema(conn)

    vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    insert_chunk(
        conn,
        source_path="test.md",
        section_title="Title",
        content_type=None,
        persona=None,
        funnel_stage=None,
        body="Test body text",
        embedding=vec,
    )

    assert count_chunks(conn) == 1

    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = cosine_top_k(conn, query, k=5)
    assert len(results) == 1
    chunk_id, score, row = results[0]
    assert score > 0.99
    assert row["body"] == "Test body text"


def test_cosine_ordering(tmp_path) -> None:
    conn = connect(tmp_path / "test.db")
    init_schema(conn)

    insert_chunk(
        conn,
        source_path="a.md",
        section_title="Close",
        content_type=None,
        persona=None,
        funnel_stage=None,
        body="Close match",
        embedding=np.array([0.9, 0.1, 0.0], dtype=np.float32),
    )
    insert_chunk(
        conn,
        source_path="b.md",
        section_title="Far",
        content_type=None,
        persona=None,
        funnel_stage=None,
        body="Far match",
        embedding=np.array([0.0, 0.0, 1.0], dtype=np.float32),
    )

    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = cosine_top_k(conn, query, k=5)
    assert len(results) == 2
    assert results[0][2]["section_title"] == "Close"
    assert results[0][1] > results[1][1]
