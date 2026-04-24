import json
import os
import uuid
from pathlib import Path

from psycopg import Connection

from shared.db import get_workspace
from shared.db import utcnow
from shared.embeddings import EmbeddingModel
from shared.jobs import add_artifact, get_job, update_job_status
from shared.storage import (
    build_normalized_object_path,
    materialize_object,
    object_uri,
    write_object,
)
from workers.local_file_source import LocalFileSource

_source = LocalFileSource()


def _infer_content_type(file_path: str) -> str:
    name = Path(file_path).stem.lower()
    if "case-study" in name or "case_study" in name:
        return "case_study"
    if "email" in name:
        return "email"
    if "landing" in name:
        return "landing_page"
    return "blog"


def _upsert_content(
    conn: Connection, *, object_path: str, raw, embedding: list[float]
) -> str:
    source_uri = object_uri(object_path)
    existing = conn.execute(
        "SELECT id, workspace_id, created_at FROM content_items WHERE source_path = %s",
        (source_uri,),
    ).fetchone()
    content_id = existing["id"] if existing else str(uuid.uuid4())
    workspace = get_workspace(conn)
    now = utcnow()
    conn.execute(
        """
        INSERT INTO content_items
        (id, workspace_id, title, body, summary, content_type, persona, funnel_stage, channel, topics, performance_score, url, source_path, embedding_json, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            workspace_id = EXCLUDED.workspace_id,
            title = EXCLUDED.title,
            body = EXCLUDED.body,
            summary = EXCLUDED.summary,
            content_type = EXCLUDED.content_type,
            persona = EXCLUDED.persona,
            funnel_stage = EXCLUDED.funnel_stage,
            channel = EXCLUDED.channel,
            topics = EXCLUDED.topics,
            performance_score = EXCLUDED.performance_score,
            url = EXCLUDED.url,
            source_path = EXCLUDED.source_path,
            embedding_json = EXCLUDED.embedding_json,
            updated_at = EXCLUDED.updated_at
        """,
        (
            content_id,
            existing["workspace_id"] if existing else workspace["id"],
            raw.title,
            raw.body,
            raw.body[:200] if len(raw.body) > 200 else raw.body,
            raw.content_type or _infer_content_type(object_path),
            "general",
            "awareness",
            "cloud_upload",
            json.dumps(raw.metadata.get("topics", [])),
            0,
            "",
            source_uri,
            json.dumps(embedding),
            existing["created_at"] if existing else now,
            now,
        ),
    )
    conn.commit()
    return content_id


def process_ingest_job(conn: Connection, job_id: str) -> dict:
    job = get_job(conn, job_id)
    workspace = get_workspace(conn)
    object_paths = job["payload"].get("object_paths", [])
    model = EmbeddingModel()
    ingested: list[dict] = []

    update_job_status(conn, job_id, status="running")

    for object_path in object_paths:
        local_path = materialize_object(object_path)
        raw = _source.extract(str(local_path))
        if raw is None:
            continue

        embedding = model.embed_text(f"{raw.title} {raw.body[:500]}")
        content_id = _upsert_content(
            conn, object_path=object_path, raw=raw, embedding=embedding
        )
        normalized_path = build_normalized_object_path(
            workspace["id"],
            job_id,
            f"{Path(object_path).stem}.txt",
        )
        normalized_uri = write_object(normalized_path, raw.body.encode("utf-8"))
        add_artifact(
            conn,
            job_id=job_id,
            kind="source-text",
            path=normalized_uri,
            preview_text=raw.body[:200],
        )
        ingested.append(
            {
                "id": content_id,
                "title": raw.title,
                "object_path": object_uri(object_path),
                "artifact_path": normalized_uri,
            }
        )
        try:
            os.unlink(local_path)
        except FileNotFoundError:
            pass

    result = {"ingested": len(ingested), "items": ingested}
    update_job_status(conn, job_id, status="succeeded", result=result)
    return result
