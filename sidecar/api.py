import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from db import get_connection, init_schema, get_content_by_id, insert_content
from search import (
    keyword_search, hybrid_search, list_all_content,
    get_content_stats, get_similar_content, get_top_performers,
)
from generated import (
    save_generated_content, get_generated_by_id,
    list_generated_content, keyword_search_generated, get_generated_stats,
)
from embeddings import EmbeddingModel
from ingest import ingest_file, ingest_directory

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None
_embedding_model: EmbeddingModel | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        settings.ensure_dirs()
        _conn = get_connection(settings.db_path)
        init_schema(_conn)
        _init_vss(_conn)
    return _conn


def _init_vss(conn: sqlite3.Connection) -> None:
    try:
        import sqlite_vss
        conn.enable_load_extension(True)
        sqlite_vss.load(conn)
        conn.enable_load_extension(False)
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vss_content USING vss0(embedding({settings.embedding_dimensions}))"
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"sqlite-vss not available: {e}")


def _get_embedding_model() -> EmbeddingModel:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_conn()
    logger.info(f"Sidecar ready on port {settings.port}")
    yield
    if _conn:
        _conn.close()


app = FastAPI(title="Content Intelligence Hub Sidecar", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "port": settings.port}


class SearchRequest(BaseModel):
    query: str
    filters: dict[str, Any] | None = None
    limit: int | None = None
    offset: int = 0


@app.get("/api/content")
def api_list_content(
    content_type: str | None = None,
    persona: str | None = None,
    funnel_stage: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    conn = _get_conn()
    filters = {}
    if content_type: filters["content_type"] = content_type
    if persona: filters["persona"] = persona
    if funnel_stage: filters["funnel_stage"] = funnel_stage
    return list_all_content(conn, filters=filters or None, limit=limit, offset=offset, search_query=search)


@app.get("/api/content/stats")
def api_content_stats():
    return get_content_stats(_get_conn())


@app.get("/api/content/{content_id}")
def api_get_content(content_id: str):
    result = get_content_by_id(_get_conn(), content_id)
    if not result:
        raise HTTPException(status_code=404, detail="Content not found")
    return result


@app.get("/api/content/{content_id}/similar")
def api_similar_content(content_id: str, limit: int = 5):
    return get_similar_content(_get_conn(), content_id, limit=limit)


@app.post("/api/content/search")
def api_search_content(req: SearchRequest):
    conn = _get_conn()
    embed = _get_embedding_model()
    query_embedding = embed.embed_text(req.query)
    results = hybrid_search(conn, req.query, query_embedding, filters=req.filters, limit=req.limit)
    return {"items": results, "query": req.query}


class RepurposeRequest(BaseModel):
    content_id: str
    formats: list[str]
    tone: str = "professional"
    custom_instructions: dict[str, str] | None = None
    save: bool = True


class QueryRequest(BaseModel):
    query: str


@app.post("/api/agents/repurpose")
def api_repurpose(req: RepurposeRequest):
    from agents.repurpose_agent import repurpose_content
    from providers.anthropic import AnthropicProvider
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")
    provider = AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)
    conn = _get_conn()
    result = repurpose_content(
        conn=conn, provider=provider,
        content_id=req.content_id, formats=req.formats,
        tone=req.tone, custom_instructions=req.custom_instructions,
    )
    if req.save and result.get("success"):
        source = get_content_by_id(conn, req.content_id)
        source_title = source["title"] if source else ""
        for fmt, body in result.get("generated_content", {}).items():
            gen_id = save_generated_content(
                conn, source_content_id=req.content_id, source_title=source_title,
                format=fmt, tone=req.tone, body=body,
                quality_score=result.get("quality_scores", {}).get(fmt),
            )
            result.setdefault("saved_ids", {})[fmt] = gen_id
    return result


@app.post("/api/agents/query")
def api_query(req: QueryRequest):
    from agents.query_agent import discover_content
    from providers.anthropic import AnthropicProvider
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")
    provider = AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)
    return discover_content(
        conn=_get_conn(), provider=provider,
        embedding_model=_get_embedding_model(), query=req.query,
    )


@app.get("/api/generated")
def api_list_generated(
    format: str | None = None,
    tone: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    filters = {}
    if format: filters["format"] = format
    if tone: filters["tone"] = tone
    return list_generated_content(_get_conn(), filters=filters or None, limit=limit, offset=offset)


@app.get("/api/generated/stats")
def api_generated_stats():
    return get_generated_stats(_get_conn())


@app.get("/api/generated/{gen_id}")
def api_get_generated(gen_id: str):
    result = get_generated_by_id(_get_conn(), gen_id)
    if not result:
        raise HTTPException(status_code=404, detail="Generated content not found")
    return result


@app.post("/api/generated/search")
def api_search_generated(req: SearchRequest):
    return {"items": keyword_search_generated(_get_conn(), req.query, limit=req.limit)}


class IngestRequest(BaseModel):
    paths: list[str]


@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    conn = _get_conn()
    embed = _get_embedding_model()
    results = []
    for path in req.paths:
        p = Path(path)
        if p.is_dir():
            results.extend(ingest_directory(conn, str(p), embed))
        elif p.is_file():
            result = ingest_file(conn, str(p), embed)
            if result:
                results.append(result)
    return {"ingested": len(results), "items": results}


class SettingsUpdate(BaseModel):
    anthropic_api_key: str | None = None
    watched_folders: list[str] | None = None


@app.get("/api/settings")
def api_get_settings():
    return {
        "anthropic_api_key_set": bool(settings.anthropic_api_key),
        "watched_folders": settings.watched_folders,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
    }


@app.put("/api/settings")
def api_update_settings(req: SettingsUpdate):
    if req.anthropic_api_key is not None:
        settings.anthropic_api_key = req.anthropic_api_key
    if req.watched_folders is not None:
        settings.watched_folders = req.watched_folders
    conn = _get_conn()
    if req.anthropic_api_key is not None:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('anthropic_api_key', ?)",
            (req.anthropic_api_key,),
        )
    if req.watched_folders is not None:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('watched_folders', ?)",
            (json.dumps(req.watched_folders),),
        )
    conn.commit()
    return {"status": "updated"}
