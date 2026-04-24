from fastapi import APIRouter, Depends

from api.deps import get_db, require_user
from shared.config import settings
from shared.db import get_workspace

router = APIRouter(tags=["settings"])


@router.get("/api/settings")
def get_settings(
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    workspace = get_workspace(conn)
    anthropic = conn.execute(
        "SELECT connected FROM integration_states WHERE provider = 'anthropic'"
    ).fetchone()
    return {
        "anthropic_api_key_set": bool(anthropic and anthropic["connected"]),
        "watched_folders": [],
        "llm_model": "claude-sonnet-4-6",
        "embedding_model": "all-MiniLM-L6-v2",
        "auth_mode": settings.auth_mode,
        "workspace_name": workspace["name"],
        "upload_mode": settings.upload_mode,
    }
