import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from shared.config import settings


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


_pool: ConnectionPool | None = None


def connection_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "dbname": settings.db_name,
        "user": settings.db_user,
        "password": settings.db_password,
        "port": settings.db_port,
        "row_factory": dict_row,
    }
    if settings.db_host_path:
        kwargs["host"] = settings.db_host_path
    return kwargs


def open_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            kwargs=connection_kwargs(),
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_connection() -> Connection:
    settings.ensure_dirs()
    return open_pool().getconn()


def release_connection(conn: Connection) -> None:
    pool = open_pool()
    pool.putconn(conn)


def init_schema(conn: Connection) -> None:
    schema_sql = """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;

        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL DEFAULT 'operator',
            workspace_id TEXT REFERENCES workspaces(id),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workspace_memberships (
            user_id TEXT NOT NULL REFERENCES users(id),
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, workspace_id)
        );

        CREATE TABLE IF NOT EXISTS magic_links (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            source_content_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT,
            error TEXT,
            created_by TEXT REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_runs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(id),
            status TEXT NOT NULL,
            worker_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS content_items (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT '',
            persona TEXT NOT NULL DEFAULT '',
            funnel_stage TEXT NOT NULL DEFAULT '',
            channel TEXT NOT NULL DEFAULT '',
            topics TEXT NOT NULL DEFAULT '[]',
            performance_score REAL NOT NULL DEFAULT 0,
            url TEXT NOT NULL DEFAULT '',
            source_path TEXT NOT NULL DEFAULT '',
            embedding_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS generated_items (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            job_id TEXT REFERENCES jobs(id),
            source_content_id TEXT REFERENCES content_items(id),
            source_title TEXT NOT NULL,
            format TEXT NOT NULL,
            tone TEXT NOT NULL,
            body TEXT NOT NULL,
            quality_score REAL,
            prompts TEXT NOT NULL DEFAULT '{}',
            artifact_path TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            job_id TEXT REFERENCES jobs(id),
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            content_type TEXT,
            preview_text TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS integration_states (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            provider TEXT NOT NULL UNIQUE,
            secret_ref TEXT,
            connected BOOLEAN NOT NULL DEFAULT FALSE,
            last_checked_at TEXT,
            last_rotated_at TEXT,
            status_message TEXT
        );

        ALTER TABLE integration_states
        ALTER COLUMN connected DROP DEFAULT;
        ALTER TABLE integration_states
        ALTER COLUMN connected TYPE BOOLEAN
        USING CASE
            WHEN connected::text IN ('0', 'false', 'f') THEN FALSE
            ELSE TRUE
        END;
        ALTER TABLE integration_states
        ALTER COLUMN connected SET DEFAULT FALSE;

        CREATE TABLE IF NOT EXISTS workspace_config (
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (workspace_id, key)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
        CREATE INDEX IF NOT EXISTS idx_content_workspace ON content_items(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_generated_workspace ON generated_items(workspace_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_generated_job_format ON generated_items(job_id, format);
        """
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()
    ensure_default_workspace(conn)
    ensure_default_integrations(conn)


def ensure_default_workspace(conn: Connection) -> str:
    row = conn.execute(
        "SELECT id FROM workspaces ORDER BY created_at LIMIT 1"
    ).fetchone()
    if row:
        return row["id"]

    workspace_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO workspaces (id, name, created_at) VALUES (%s, %s, %s)",
        (workspace_id, settings.default_workspace_name, utcnow()),
    )
    conn.commit()
    return workspace_id


def ensure_default_integrations(conn: Connection) -> None:
    workspace_id = ensure_default_workspace(conn)
    defaults = [
        ("anthropic", settings.anthropic_secret_ref, False, "Pending configuration"),
        (
            "gcs",
            "gcs_bucket",
            bool(settings.artifact_bucket),
            f"Bucket {settings.artifact_bucket or 'unconfigured'}",
        ),
        ("magic_link", "magic_link_secret", True, "Magic-link auth enabled"),
    ]
    for provider, secret_ref, connected, status_message in defaults:
        conn.execute(
            """
            INSERT INTO integration_states
            (id, workspace_id, provider, secret_ref, connected, status_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider) DO UPDATE
            SET secret_ref = EXCLUDED.secret_ref,
                connected = EXCLUDED.connected,
                status_message = EXCLUDED.status_message
            """,
            (
                str(uuid.uuid4()),
                workspace_id,
                provider,
                secret_ref,
                connected,
                status_message,
            ),
        )
    conn.commit()


@contextmanager
def managed_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)


def get_workspace(conn: Connection) -> dict:
    return conn.execute(
        "SELECT * FROM workspaces ORDER BY created_at LIMIT 1"
    ).fetchone()


def row_to_dict(row: dict | None) -> dict | None:
    return dict(row) if row is not None else None


def list_rows(conn: Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def json_dumps(value: dict | list | None) -> str:
    return json.dumps(value or {})
