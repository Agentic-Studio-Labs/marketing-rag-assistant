"""Tests for cloud natural-language discover (keyword search + LLM orchestration)."""

from unittest.mock import MagicMock

import pytest

from shared.query_agent import cloud_keyword_search, discover_content_cloud


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    return conn


def test_cloud_keyword_search_builds_workspace_clause(mock_conn):
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        {
            "id": "a1",
            "title": "Hello",
            "summary": "S",
            "body": "B",
            "content_type": "blog",
            "persona": "cto",
            "workspace_id": "ws1",
        }
    ]
    mock_conn.execute.return_value = mock_result

    rows = cloud_keyword_search(
        mock_conn,
        "ws1",
        "kubernetes",
        {"content_type": "blog"},
        limit=5,
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Hello"
    assert "embedding_json" not in rows[0]

    sql = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1]
    assert "workspace_id = %s" in sql
    assert "content_type = %s" in sql
    assert "ws1" in params
    assert "blog" in params


def test_discover_content_cloud_calls_llm_twice(mock_conn):
    provider = MagicMock()
    provider.complete.side_effect = [
        '{"search_terms": "ai", "filters": {}}',
        "Here is what we found.",
    ]
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        {
            "id": "x",
            "title": "AI Post",
            "summary": "Sum",
            "body": "Body",
            "content_type": "blog",
            "persona": "cto",
            "funnel_stage": "awareness",
            "channel": "",
            "topics": "[]",
            "performance_score": 50.0,
            "url": "",
            "source_path": "",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "workspace_id": "ws1",
        }
    ]
    mock_conn.execute.return_value = mock_result

    out = discover_content_cloud(mock_conn, provider, "tell me about AI", "ws1")

    assert provider.complete.call_count == 2
    assert out["query"] == "tell me about AI"
    assert out["answer"] == "Here is what we found."
    assert len(out["results"]) == 1
    assert out["results"][0]["title"] == "AI Post"
    assert out["search_terms"] == "ai"
