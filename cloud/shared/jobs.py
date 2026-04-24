import json
import uuid

from psycopg import Connection

from shared.db import get_workspace, list_rows, utcnow


def create_job(
    conn: Connection,
    *,
    job_type: str,
    payload: dict,
    created_by: str | None,
    source_content_id: str | None = None,
) -> dict:
    workspace = get_workspace(conn)
    job_id = str(uuid.uuid4())
    now = utcnow()
    conn.execute(
        """
        INSERT INTO jobs
        (id, workspace_id, job_type, status, source_content_id, payload_json, created_by, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            job_id,
            workspace["id"],
            job_type,
            "queued",
            source_content_id,
            json.dumps(payload),
            created_by,
            now,
            now,
        ),
    )
    conn.commit()
    return get_job(conn, job_id)


def get_job(conn: Connection, job_id: str) -> dict:
    row = conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)).fetchone()
    if row is None:
        raise KeyError(job_id)

    artifacts = list_rows(
        conn,
        "SELECT * FROM artifacts WHERE job_id = %s ORDER BY created_at DESC",
        (job_id,),
    )
    result = dict(row)
    result["payload"] = json.loads(result.pop("payload_json") or "{}")
    result["result"] = json.loads(result.pop("result_json") or "null")
    result["artifacts"] = artifacts
    return result


def list_jobs(
    conn: Connection, *, job_type: str | None = None, status: str | None = None
) -> list[dict]:
    clauses = ["1=1"]
    params: list[str] = []
    if job_type:
        clauses.append("job_type = %s")
        params.append(job_type)
    if status:
        clauses.append("status = %s")
        params.append(status)

    rows = list_rows(
        conn,
        f"SELECT * FROM jobs WHERE {' AND '.join(clauses)} ORDER BY created_at DESC",
        tuple(params),
    )
    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "job_type": row["job_type"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "source_content_id": row["source_content_id"],
                "result_preview": None,
            }
        )
    return items


def update_job_status(
    conn: Connection,
    job_id: str,
    *,
    status: str,
    error: str | None = None,
    result: dict | None = None,
) -> None:
    conn.execute(
        "UPDATE jobs SET status = %s, error = %s, result_json = %s, updated_at = %s WHERE id = %s",
        (
            status,
            error,
            json.dumps(result) if result is not None else None,
            utcnow(),
            job_id,
        ),
    )
    conn.commit()


def add_artifact(
    conn: Connection,
    *,
    job_id: str,
    kind: str,
    path: str,
    content_type: str = "text/plain",
    preview_text: str | None = None,
) -> None:
    workspace = get_workspace(conn)
    conn.execute(
        """
        INSERT INTO artifacts (id, workspace_id, job_id, kind, path, content_type, preview_text, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            workspace["id"],
            job_id,
            kind,
            path,
            content_type,
            preview_text,
            utcnow(),
        ),
    )
    conn.commit()


def transition_job_to_running(conn: Connection, job_id: str) -> bool:
    row = conn.execute(
        """
        UPDATE jobs
        SET status = %s, updated_at = %s
        WHERE id = %s AND status = %s
        RETURNING id
        """,
        ("running", utcnow(), job_id, "queued"),
    ).fetchone()
    conn.commit()
    return row is not None
