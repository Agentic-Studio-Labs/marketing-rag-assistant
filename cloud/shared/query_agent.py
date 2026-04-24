"""Natural-language content discovery (cloud): LLM extracts filters + Postgres keyword search."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from psycopg import Connection

from shared.providers.base import LLMProvider, Message

logger = logging.getLogger(__name__)

FILTER_EXTRACTION_PROMPT = """Extract search parameters from the user's query.

Return a JSON object with:
- "search_terms": the core search keywords (string)
- "filters": an object with optional keys:
  - "content_type": one of [blog, case_study, email, social_post, landing_page, whitepaper] or null
  - "persona": one of [cto, cfo, developer, marketing_leader, engineer, ceo, cmo] or null
  - "funnel_stage": one of [awareness, consideration, decision, retention] or null
  - "performance_score_gte": minimum performance score (number) or null

Only include filter keys when the user explicitly mentions them or clearly implies them.

<examples>
Query: "Find blog posts about kubernetes for CTOs"
{{"search_terms": "kubernetes", "filters": {{"content_type": "blog", "persona": "cto"}}}}

Query: "high performing content about AI"
{{"search_terms": "AI", "filters": {{"performance_score_gte": 70}}}}

Query: "tell me about cloud migration"
{{"search_terms": "cloud migration", "filters": {{}}}}
</examples>

User query: {query}

Respond with ONLY the JSON object, no other text."""

ANSWER_PROMPT = """Based on the search results below, provide a concise natural language answer to the user's query.

<query>{query}</query>

<results>
{results_text}
</results>

Summarize the key findings. Reference specific content by title. Be concise (2-4 sentences)."""


def extract_filters(provider: LLMProvider, query: str) -> dict[str, Any]:
    prompt = FILTER_EXTRACTION_PROMPT.format(query=query)
    response = provider.complete(
        messages=[Message(role="user", content=prompt)],
        system="You extract structured search parameters from natural language. Respond with JSON only.",
        temperature=0.0,
        max_tokens=256,
    )
    text = response.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse filter response: %s", text[:200])
        return {"search_terms": query, "filters": {}}


def _clean_filters(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if v is None or v == "":
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        out[str(k)] = v
    return out


def _format_results_for_answer(results: list[dict], limit: int = 5) -> str:
    lines: list[str] = []
    for i, r in enumerate(results[:limit], 1):
        lines.append(
            f"{i}. **{r.get('title', 'Untitled')}** ({r.get('content_type', '')})"
        )
        if r.get("summary"):
            lines.append(f"   {str(r['summary'])[:200]}")
        lines.append("")
    return "\n".join(lines)


def _strip_row(row: dict) -> dict:
    out = dict(row)
    out.pop("embedding_json", None)
    return out


def cloud_keyword_search(
    conn: Connection,
    workspace_id: str | None,
    search_terms: str,
    filters: dict[str, Any],
    *,
    limit: int = 10,
) -> list[dict]:
    terms = (search_terms or "").strip()
    if not terms:
        return []
    q = f"%{terms}%"
    clauses = ["(title ILIKE %s OR summary ILIKE %s OR body ILIKE %s)"]
    params: list[Any] = [q, q, q]
    if workspace_id is not None:
        clauses.append("workspace_id = %s")
        params.append(workspace_id)
    for key in ("content_type", "persona", "funnel_stage", "channel"):
        val = filters.get(key)
        if val is not None and val != "":
            clauses.append(f"{key} = %s")
            params.append(str(val))
    if filters.get("performance_score_gte") is not None:
        clauses.append("performance_score >= %s")
        params.append(float(filters["performance_score_gte"]))
    sql = f"""
        SELECT * FROM content_items
        WHERE {" AND ".join(clauses)}
        ORDER BY updated_at DESC
        LIMIT %s
    """
    params.append(limit)
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [_strip_row(dict(r)) for r in rows]


def discover_content_cloud(
    conn: Connection,
    provider: LLMProvider,
    query: str,
    workspace_id: str | None,
) -> dict[str, Any]:
    extracted = extract_filters(provider, query)
    search_terms = extracted.get("search_terms") or query
    if not isinstance(search_terms, str):
        search_terms = str(search_terms)
    filters = _clean_filters(extracted.get("filters", {}))
    results = cloud_keyword_search(conn, workspace_id, search_terms, filters, limit=10)
    results_text = _format_results_for_answer(results)
    answer_prompt = ANSWER_PROMPT.format(query=query, results_text=results_text)
    answer = provider.complete(
        messages=[Message(role="user", content=answer_prompt)],
        system="You are a helpful content discovery assistant. Be concise and specific.",
        temperature=0.3,
    )
    return {
        "query": query,
        "answer": answer,
        "results": results,
        "filters_applied": filters,
        "search_terms": search_terms,
    }
