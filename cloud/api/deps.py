from fastapi import Depends, Header, HTTPException

from shared.auth import get_user_for_session
from shared.db import get_connection, release_connection


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)


def require_user(
    authorization: str | None = Header(default=None),
    conn=Depends(get_db),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return get_user_for_session(conn, token)
