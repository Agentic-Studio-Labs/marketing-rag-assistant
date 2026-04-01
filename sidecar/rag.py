from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from config import SIMILARITY_THRESHOLD, TOP_K
from db import cosine_top_k
from embed import embed_texts
from llm import LLMResult, generate_answer


@dataclass
class Source:
    chunk_id: int
    title: str | None
    score: float
    excerpt: str


@dataclass
class QueryResult:
    text: str
    sources: list[Source]
    llm: LLMResult | None


def retrieve(conn: sqlite3.Connection, query: str) -> tuple[list[Source], list[str]]:
    qv = embed_texts([query])[0]
    ranked = cosine_top_k(conn, qv, TOP_K * 3)

    sources: list[Source] = []
    texts: list[str] = []
    for chunk_id, score, row in ranked:
        if score < SIMILARITY_THRESHOLD:
            continue
        body = str(row["body"])
        excerpt = body[:400] + ("…" if len(body) > 400 else "")
        sources.append(
            Source(
                chunk_id=chunk_id,
                title=row["section_title"],
                score=score,
                excerpt=excerpt,
            )
        )
        texts.append(body)
        if len(sources) >= TOP_K:
            break

    return sources, texts


def answer_query(conn: sqlite3.Connection, query: str) -> QueryResult:
    sources, blocks = retrieve(conn, query)
    if not blocks:
        msg = (
            "No sufficiently relevant chunks were found. "
            "Try different wording or lower RAG_SIM_THRESHOLD."
        )
        return QueryResult(text=msg, sources=[], llm=None)
    result = generate_answer(query, blocks)
    return QueryResult(text=result.text, sources=sources, llm=result)
