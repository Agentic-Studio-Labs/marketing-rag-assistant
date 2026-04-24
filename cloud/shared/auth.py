import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, UTC

from fastapi import HTTPException
from psycopg import Connection

from shared.config import settings
from shared.db import get_workspace, utcnow


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_payload(payload: dict, secret: str) -> str:
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).digest()
    return f"{body}.{_b64encode(signature)}"


def verify_signed_payload(token: str, secret: str) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid token format") from exc

    expected = hmac.new(
        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).digest()
    provided = _b64decode(signature)
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=400, detail="Invalid token signature")

    payload = json.loads(_b64decode(body))
    expires_at = datetime.fromisoformat(payload["expires_at"])
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Token expired")
    return payload


def email_allowed(email: str) -> bool:
    allowed = [
        item.strip()
        for item in settings.allowed_email_domains.split(",")
        if item.strip()
    ]
    if "*" in allowed:
        return True
    domain = email.split("@")[-1].lower()
    return domain in {item.lower() for item in allowed}


def ensure_user(conn: Connection, email: str) -> dict:
    row = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    if row:
        return dict(row)

    if not email_allowed(email):
        raise HTTPException(status_code=403, detail="Email domain is not allowed")

    workspace = get_workspace(conn)
    user_id = str(uuid.uuid4())
    created_at = utcnow()
    conn.execute(
        """
        INSERT INTO users (id, email, role, workspace_id, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, email, "operator", workspace["id"], created_at),
    )
    conn.execute(
        """
        INSERT INTO workspace_memberships (user_id, workspace_id, role, created_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, workspace_id) DO NOTHING
        """,
        (user_id, workspace["id"], "operator", created_at),
    )
    conn.commit()
    return {
        "id": user_id,
        "email": email,
        "role": "operator",
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
    }


def create_magic_link(conn: Connection, email: str) -> str:
    ensure_user(conn, email)
    payload = {
        "kind": "magic_link",
        "email": email,
        "nonce": secrets.token_urlsafe(12),
        "expires_at": (
            datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes)
        ).isoformat(),
    }
    token = sign_payload(payload, settings.magic_link_secret)
    conn.execute(
        """
        INSERT INTO magic_links (id, email, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), email, hash_token(token), payload["expires_at"], utcnow()),
    )
    conn.commit()
    return token


def exchange_magic_link(conn: Connection, token: str) -> dict:
    payload = verify_signed_payload(token, settings.magic_link_secret)
    if payload.get("kind") != "magic_link":
        raise HTTPException(status_code=400, detail="Unexpected token type")

    token_hash = hash_token(token)
    row = conn.execute(
        "SELECT * FROM magic_links WHERE token_hash = %s AND used_at IS NULL",
        (token_hash,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=400, detail="Magic link already used or unknown"
        )

    email = payload["email"]
    user = ensure_user(conn, email)
    conn.execute(
        "UPDATE magic_links SET used_at = %s WHERE token_hash = %s",
        (utcnow(), token_hash),
    )
    conn.commit()
    session = create_session(conn, user["id"])
    return {"session": session, "user": user}


def create_session(conn: Connection, user_id: str) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    ).isoformat()
    conn.execute(
        """
        INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), user_id, hash_token(token), expires_at, utcnow()),
    )
    conn.commit()
    return {"token": token, "expires_at": expires_at}


def get_user_for_session(conn: Connection, token: str) -> dict:
    token_hash = hash_token(token)
    row = conn.execute(
        """
        SELECT users.*, workspaces.name AS workspace_name
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        LEFT JOIN workspaces ON workspaces.id = users.workspace_id
        WHERE sessions.token_hash = %s AND sessions.revoked_at IS NULL
        """,
        (token_hash,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    session_row = conn.execute(
        "SELECT expires_at FROM sessions WHERE token_hash = %s",
        (token_hash,),
    ).fetchone()
    expires_at = datetime.fromisoformat(session_row["expires_at"])
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired")

    return dict(row)


def revoke_session(conn: Connection, token: str) -> None:
    conn.execute(
        "UPDATE sessions SET revoked_at = %s WHERE token_hash = %s",
        (utcnow(), hash_token(token)),
    )
    conn.commit()
