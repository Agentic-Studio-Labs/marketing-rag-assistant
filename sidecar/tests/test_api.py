from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.pop("ANTHROPIC_API_KEY", None)


@pytest.fixture()
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch.dict(os.environ, {"RAG_DB_PATH": db_path}):
        import importlib

        import config as cfg

        importlib.reload(cfg)

        from api import app

        with TestClient(app) as c:
            yield c


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_query_returns_structured_response(client: TestClient) -> None:
    r = client.post("/api/query", json={"query": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "sources" in body
    assert isinstance(body["sources"], list)


def test_query_rejects_empty(client: TestClient) -> None:
    r = client.post("/api/query", json={"query": ""})
    assert r.status_code == 422
