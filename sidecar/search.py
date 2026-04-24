import sqlite3
import json
from config import settings


def _apply_filters(query: str, params: list, filters: dict | None) -> tuple[str, list]:
    if not filters:
        return query, params
    clauses = []
    for key in ("content_type", "persona", "funnel_stage", "channel"):
        if key in filters and filters[key]:
            clauses.append(f"mc.{key} = ?")
            params.append(filters[key])
    if "performance_score_gte" in filters:
        clauses.append("mc.performance_score >= ?")
        params.append(filters["performance_score_gte"])
    if clauses:
        query += " AND " + " AND ".join(clauses)
    return query, params


def keyword_search(
    conn: sqlite3.Connection,
    query: str,
    filters: dict | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    limit = limit or settings.search_limit
    fts_query = query.replace('"', '""')
    sql = """
        SELECT mc.*, bm25(content_fts) AS rank
        FROM content_fts
        JOIN marketing_content mc ON mc.rowid = content_fts.rowid
        WHERE content_fts MATCH ?
    """
    params: list = [f'"{fts_query}"']
    sql, params = _apply_filters(sql, params, filters)
    sql += " ORDER BY rank LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    query_embedding: list[float],
    filters: dict | None = None,
    alpha: float | None = None,
    limit: int | None = None,
) -> list[dict]:
    alpha = alpha if alpha is not None else settings.hybrid_alpha
    limit = limit or settings.search_limit
    fetch_k = limit * 3

    keyword_results = keyword_search(conn, query, filters=filters, limit=fetch_k)
    keyword_scores: dict[str, float] = {}
    keyword_items: dict[str, dict] = {}
    if keyword_results:
        max_rank = max(abs(r["rank"]) for r in keyword_results) or 1.0
        for r in keyword_results:
            row = dict(r)
            row.pop("rank", None)
            keyword_scores[r["id"]] = abs(r["rank"]) / max_rank
            keyword_items[r["id"]] = row

    vector_scores: dict[str, float] = {}
    vector_items: dict[str, dict] = {}
    try:
        vss_count = conn.execute("SELECT COUNT(*) FROM vss_content").fetchone()[0]
        if vss_count == 0:
            raise ValueError("empty vss index")
        vss_rows = conn.execute(
            "SELECT rowid, distance FROM vss_content WHERE vss_search(embedding, vss_search_params(?, ?))",
            [json.dumps(query_embedding), min(fetch_k, vss_count)],
        ).fetchall()
        if vss_rows:
            for vr in vss_rows:
                mc_row = conn.execute(
                    "SELECT * FROM marketing_content WHERE rowid = ?", (vr["rowid"],)
                ).fetchone()
                if mc_row:
                    item = dict(mc_row)
                    if filters and not _passes_filters(item, filters):
                        continue
                    sim = max(0.0, 1.0 - vr["distance"])
                    vector_scores[item["id"]] = sim
                    vector_items[item["id"]] = item
    except Exception:
        pass

    all_ids = set(keyword_scores.keys()) | set(vector_scores.keys())
    scored: list[tuple[str, float]] = []
    for cid in all_ids:
        ks = keyword_scores.get(cid, 0.0)
        vs = vector_scores.get(cid, 0.0)
        combined = alpha * vs + (1 - alpha) * ks
        scored.append((cid, combined))

    scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for cid, score in scored[:limit]:
        item = keyword_items.get(cid) or vector_items.get(cid)
        if item:
            item["score"] = round(score, 4)
            results.append(item)
    return results


def _passes_filters(item: dict, filters: dict) -> bool:
    for key in ("content_type", "persona", "funnel_stage", "channel"):
        if key in filters and filters[key] and item.get(key) != filters[key]:
            return False
    if "performance_score_gte" in filters:
        if (item.get("performance_score") or 0) < filters["performance_score_gte"]:
            return False
    return True


def get_similar_content(
    conn: sqlite3.Connection,
    content_id: str,
    limit: int = 5,
) -> list[dict]:
    source = conn.execute(
        "SELECT rowid FROM marketing_content WHERE id = ?", (content_id,)
    ).fetchone()
    if not source:
        return []
    source_rowid = source["rowid"]
    try:
        vss_count = conn.execute("SELECT COUNT(*) FROM vss_content").fetchone()[0]
        if vss_count < 2:
            return []
        vss_rows = conn.execute(
            "SELECT rowid, distance FROM vss_content WHERE vss_search("
            "embedding, vss_search_params("
            "(SELECT embedding FROM vss_content WHERE rowid = ?), ?))",
            [source_rowid, min(limit + 1, vss_count)],
        ).fetchall()
    except Exception:
        return []
    results = []
    for vr in vss_rows:
        if vr["rowid"] == source_rowid:
            continue
        row = conn.execute(
            "SELECT * FROM marketing_content WHERE rowid = ?", (vr["rowid"],)
        ).fetchone()
        if row:
            item = dict(row)
            item["distance"] = vr["distance"]
            results.append(item)
    return results[:limit]


def list_all_content(
    conn: sqlite3.Connection,
    filters: dict | None = None,
    limit: int | None = None,
    offset: int = 0,
    search_query: str | None = None,
) -> dict:
    limit = limit or settings.search_limit
    if search_query:
        items = keyword_search(conn, search_query, filters=filters, limit=limit, offset=offset)
        fts_query = search_query.replace('"', '""')
        count_sql = """
            SELECT COUNT(*) FROM content_fts
            JOIN marketing_content mc ON mc.rowid = content_fts.rowid
            WHERE content_fts MATCH ?
        """
        count_params: list = [f'"{fts_query}"']
        count_sql, count_params = _apply_filters(count_sql, count_params, filters)
        total = conn.execute(count_sql, count_params).fetchone()[0]
    else:
        sql = "SELECT mc.* FROM marketing_content mc WHERE 1=1"
        params: list = []
        sql, params = _apply_filters(sql, params, filters)
        count_sql_plain = sql.replace("SELECT mc.*", "SELECT COUNT(*)")
        total = conn.execute(count_sql_plain, params).fetchone()[0]
        sql += " ORDER BY mc.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        items = [dict(r) for r in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


def get_content_stats(conn: sqlite3.Connection) -> dict:
    stats = {}
    for col in ("content_type", "persona", "funnel_stage", "channel"):
        rows = conn.execute(
            f"SELECT {col}, COUNT(*) as cnt FROM marketing_content WHERE {col} != '' GROUP BY {col}"
        ).fetchall()
        stats[f"by_{col}"] = {r[0]: r[1] for r in rows}
    total = conn.execute("SELECT COUNT(*) FROM marketing_content").fetchone()[0]
    avg_perf = conn.execute(
        "SELECT COALESCE(AVG(performance_score), 0) FROM marketing_content"
    ).fetchone()[0]
    stats["total"] = total
    stats["avg_performance"] = round(avg_perf, 1)
    return stats


def get_top_performers(
    conn: sqlite3.Connection, limit: int = 10, min_score: float = 0
) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM marketing_content WHERE performance_score >= ? "
        "ORDER BY performance_score DESC LIMIT ?",
        (min_score, limit),
    ).fetchall()
    return [dict(r) for r in rows]
