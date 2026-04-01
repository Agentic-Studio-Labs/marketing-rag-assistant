from __future__ import annotations

import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bootstrap import ensure_indexed, reindex_corpus
from config import CORPUS_DIR
from db import (
    connect,
    count_audit_log,
    get_audit_log,
    init_schema,
    insert_chunk,
    log_event,
)
from embed import embed_texts
from ingest import load_chunks
from rag import Source, answer_query

ALLOWED_EXTENSIONS = {".md", ".pdf"}


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)


class SourceOut(BaseModel):
    chunk_id: int
    title: str | None
    score: float
    excerpt: str


class UsageOut(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    usage: UsageOut | None = None


def _source_to_out(s: Source) -> SourceOut:
    return SourceOut(
        chunk_id=s.chunk_id,
        title=s.title,
        score=s.score,
        excerpt=s.excerpt,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    ensure_indexed(conn)
    app.state.db = conn
    log_event(conn, "system", "Sidecar started")
    try:
        yield
    finally:
        log_event(conn, "system", "Sidecar stopping")
        conn.close()


app = FastAPI(title="Marketing RAG sidecar", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def query(payload: QueryBody, request: Request) -> QueryResponse:
    conn = request.app.state.db
    q = payload.query.strip()
    try:
        result = answer_query(conn, q)
        source_ids = [s.chunk_id for s in result.sources]
        audit_detail: dict[str, object] = {
            "query": q,
            "sources": source_ids,
            "source_count": len(result.sources),
        }
        usage_out: UsageOut | None = None
        if result.llm:
            audit_detail["model"] = result.llm.model
            audit_detail["input_tokens"] = result.llm.input_tokens
            audit_detail["output_tokens"] = result.llm.output_tokens
            audit_detail["cost_usd"] = round(result.llm.cost_usd, 6)
            usage_out = UsageOut(
                model=result.llm.model,
                input_tokens=result.llm.input_tokens,
                output_tokens=result.llm.output_tokens,
                cost_usd=result.llm.cost_usd,
            )
        log_event(
            conn,
            "query",
            json.dumps(audit_detail, ensure_ascii=False),
        )
        return QueryResponse(
            answer=result.text,
            sources=[_source_to_out(s) for s in result.sources],
            usage=usage_out,
        )
    except Exception as exc:
        log_event(
            conn,
            "error",
            json.dumps({"action": "query", "error": str(exc)}),
        )
        raise


@app.get("/api/corpus")
def corpus(request: Request) -> dict[str, Any]:
    conn = request.app.state.db
    rows = conn.execute(
        """
        SELECT id, source_path, section_title, content_type, persona,
               funnel_stage, length(body) AS body_len
        FROM chunks
        ORDER BY source_path, id
        """
    ).fetchall()

    docs: dict[str, dict[str, Any]] = {}
    for r in rows:
        sp = r["source_path"]
        if sp not in docs:
            docs[sp] = {
                "source_path": sp,
                "chunk_count": 0,
                "total_chars": 0,
                "chunks": [],
            }
        docs[sp]["chunk_count"] += 1
        docs[sp]["total_chars"] += r["body_len"] or 0
        docs[sp]["chunks"].append(
            {
                "id": r["id"],
                "section_title": r["section_title"],
                "content_type": r["content_type"],
                "persona": r["persona"],
                "funnel_stage": r["funnel_stage"],
                "body_len": r["body_len"],
            }
        )

    return {
        "total_documents": len(docs),
        "total_chunks": len(rows),
        "documents": list(docs.values()),
    }


@app.get("/api/chunks/{chunk_id}")
def get_chunk(chunk_id: int, request: Request) -> dict[str, Any]:
    conn = request.app.state.db
    row = conn.execute(
        """
        SELECT id, source_path, section_title, content_type, persona,
               funnel_stage, body, created_at
        FROM chunks WHERE id = ?
        """,
        (chunk_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {
        "id": row["id"],
        "source_path": row["source_path"],
        "section_title": row["section_title"],
        "content_type": row["content_type"],
        "persona": row["persona"],
        "funnel_stage": row["funnel_stage"],
        "body": row["body"],
        "created_at": row["created_at"],
    }


@app.post("/api/upload")
async def upload(file: UploadFile, request: Request) -> dict[str, Any]:
    conn = request.app.state.db
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        log_event(
            conn,
            "error",
            json.dumps({"action": "upload", "error": f"Rejected {ext}"}),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed}",
        )

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    dest = CORPUS_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        chunks = load_chunks(dest, CORPUS_DIR)
        if not chunks:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="No extractable text")

        bodies = [str(c["body"]) for c in chunks]
        vectors = embed_texts(bodies)

        init_schema(conn)
        inserted = 0
        for chunk, vec in zip(chunks, vectors, strict=True):
            insert_chunk(
                conn,
                source_path=str(chunk["source_path"]),
                section_title=chunk.get("section_title"),
                content_type=chunk.get("content_type"),
                persona=chunk.get("persona"),
                funnel_stage=chunk.get("funnel_stage"),
                body=str(chunk["body"]),
                embedding=vec,
                commit=False,
            )
            inserted += 1
        conn.commit()

        log_event(
            conn,
            "upload",
            json.dumps(
                {"filename": file.filename, "chunks": inserted},
                ensure_ascii=False,
            ),
        )
        return {"filename": file.filename, "chunks_added": inserted}
    except HTTPException:
        raise
    except Exception as exc:
        log_event(
            conn,
            "error",
            json.dumps({"action": "upload", "error": str(exc)}),
        )
        raise


@app.post("/api/reindex")
def reindex(request: Request) -> dict[str, Any]:
    conn = request.app.state.db
    try:
        reindex_corpus(conn)
        from db import count_chunks

        n = count_chunks(conn)
        log_event(conn, "reindex", json.dumps({"chunks_after": n}))
        return {"ok": True}
    except Exception as exc:
        log_event(
            conn,
            "error",
            json.dumps({"action": "reindex", "error": str(exc)}),
        )
        raise


@app.post("/api/audit/key-change")
def audit_key_change(request: Request) -> dict[str, str]:
    conn = request.app.state.db
    log_event(conn, "key_change", "API key updated via settings")
    return {"status": "logged"}


@app.get("/api/audit")
def audit(
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    conn = request.app.state.db
    events = get_audit_log(conn, limit=limit, offset=offset)
    total = count_audit_log(conn)
    return {"events": events, "total": total}
