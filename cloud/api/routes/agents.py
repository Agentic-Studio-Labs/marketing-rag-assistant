from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_db, require_user
from shared.config import settings
from shared.providers.anthropic import AnthropicProvider
from shared.query_agent import discover_content_cloud

router = APIRouter(prefix="/api/agents", tags=["agents"])


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def agents_query(
    req: QueryRequest,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="Anthropic API key not configured for cloud API",
        )
    provider = AnthropicProvider(
        api_key=settings.anthropic_api_key,
        model=settings.llm_model,
    )
    return discover_content_cloud(
        conn,
        provider,
        req.query,
        user.get("workspace_id"),
    )
