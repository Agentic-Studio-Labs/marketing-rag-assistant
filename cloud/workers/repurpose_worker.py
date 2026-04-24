import uuid

from psycopg import Connection

from shared.config import settings
from shared.db import get_workspace, utcnow
from shared.jobs import (
    add_artifact,
    get_job,
    transition_job_to_running,
    update_job_status,
)
from shared.providers.anthropic import AnthropicProvider
from shared.storage import build_generated_object_path, write_object
from workers.repurpose_graph import build_repurpose_graph


def _get_provider() -> AnthropicProvider:
    api_key = settings.anthropic_api_key or ""
    if not api_key:
        raise RuntimeError("CIH_CLOUD_ANTHROPIC_API_KEY is not configured")
    return AnthropicProvider(api_key=api_key)


def process_repurpose_job(conn: Connection, job_id: str) -> dict:
    job = get_job(conn, job_id)
    if job["status"] == "succeeded":
        return job["result"] or {}
    if job["status"] == "failed":
        raise RuntimeError(job.get("error") or "Job already failed")
    if not transition_job_to_running(conn, job_id):
        current = get_job(conn, job_id)
        if current["status"] == "succeeded":
            return current["result"] or {}
        raise RuntimeError(f"Job is already {current['status']}")
    payload = job["payload"]
    source_content_id = payload["content_id"]
    source = conn.execute(
        "SELECT * FROM content_items WHERE id = %s",
        (source_content_id,),
    ).fetchone()
    if source is None:
        update_job_status(
            conn, job_id, status="failed", error="Source content not found"
        )
        raise ValueError("Source content not found")

    provider = _get_provider()
    source_dict = dict(source)
    workspace = get_workspace(conn)
    app = build_repurpose_graph(provider)
    final_state = app.invoke(
        {
            "source_content": source_dict,
            "requested_formats": payload.get("formats", []),
            "tone": payload.get("tone", "professional"),
            "custom_instructions": payload.get("custom_instructions", {}),
            "generated_content": {},
            "quality_scores": {},
            "errors": [],
        }
    )

    generated_content: dict[str, str] = final_state.get("generated_content", {})
    quality_scores: dict[str, float] = final_state.get("quality_scores", {})
    analysis = final_state.get("analysis", {})
    saved_ids: dict[str, str] = {}

    for fmt, body in generated_content.items():
        object_path = build_generated_object_path(
            source_dict.get("workspace_id") or workspace["id"],
            job_id,
            f"{fmt}.txt",
        )
        object_uri = write_object(object_path, body.encode("utf-8"))
        add_artifact(
            conn,
            job_id=job_id,
            kind=fmt,
            path=object_uri,
            preview_text=body[:200],
        )

        generated_id = str(uuid.uuid4())
        saved_ids[fmt] = generated_id
        conn.execute(
            """
            INSERT INTO generated_items
            (id, workspace_id, job_id, source_content_id, source_title, format, tone, body, quality_score, prompts, artifact_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_id, format) DO UPDATE SET
                body = EXCLUDED.body,
                quality_score = EXCLUDED.quality_score,
                prompts = EXCLUDED.prompts,
                artifact_path = EXCLUDED.artifact_path,
                created_at = EXCLUDED.created_at
            """,
            (
                generated_id,
                source_dict.get("workspace_id"),
                job_id,
                source_content_id,
                source_dict["title"],
                fmt,
                payload.get("tone", "professional"),
                body,
                quality_scores[fmt],
                "{}",
                object_uri,
                utcnow(),
            ),
        )

    conn.commit()
    result = {
        "success": len(generated_content) > 0,
        "generated_content": generated_content,
        "quality_scores": quality_scores,
        "analysis": analysis,
        "errors": final_state.get("errors", []),
        "saved_ids": saved_ids,
    }
    update_job_status(conn, job_id, status="succeeded", result=result)
    return result
