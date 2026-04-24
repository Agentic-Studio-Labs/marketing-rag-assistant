from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_db, require_user

router = APIRouter(prefix="/api/content", tags=["content"])


class SearchRequest(BaseModel):
    query: str
    filters: dict[str, str] | None = None


@router.get("")
def list_content(
    limit: int = Query(default=50),
    offset: int = Query(default=0),
    search: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    persona: str | None = Query(default=None),
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    clauses = ["1=1"]
    params: list[object] = []
    if search:
        clauses.append("(title ILIKE %s OR summary ILIKE %s OR body ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if content_type:
        clauses.append("content_type = %s")
        params.append(content_type)
    if persona:
        clauses.append("persona = %s")
        params.append(persona)

    total = conn.execute(
        f"SELECT COUNT(*) AS count FROM content_items WHERE {' AND '.join(clauses)}",
        tuple(params),
    ).fetchone()["count"]
    rows = conn.execute(
        f"""
        SELECT * FROM content_items
        WHERE {" AND ".join(clauses)}
        ORDER BY updated_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [limit, offset]),
    ).fetchall()
    items = [dict(row) for row in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@router.post("/search")
def search_content(
    req: SearchRequest,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    filters = req.filters or {}
    query = req.query
    clauses = ["(title ILIKE %s OR summary ILIKE %s OR body ILIKE %s)"]
    params: list[object] = [f"%{query}%", f"%{query}%", f"%{query}%"]
    if filters.get("content_type"):
        clauses.append("content_type = %s")
        params.append(filters["content_type"])
    if filters.get("persona"):
        clauses.append("persona = %s")
        params.append(filters["persona"])
    rows = conn.execute(
        f"""
        SELECT * FROM content_items
        WHERE {" AND ".join(clauses)}
        ORDER BY updated_at DESC
        LIMIT 25
        """,
        tuple(params),
    ).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "query": query,
    }


@router.get("/stats")
def content_stats(
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    total = conn.execute("SELECT COUNT(*) AS count FROM content_items").fetchone()[
        "count"
    ]
    avg_performance = conn.execute(
        "SELECT COALESCE(AVG(performance_score), 0) AS avg_performance FROM content_items"
    ).fetchone()["avg_performance"]

    def group(column: str) -> dict[str, int]:
        rows = conn.execute(
            f"SELECT {column}, COUNT(*) AS count FROM content_items WHERE {column} != '' GROUP BY {column}"
        ).fetchall()
        return {row[column]: row["count"] for row in rows}

    return {
        "total": total,
        "avg_performance": round(avg_performance, 1),
        "by_content_type": group("content_type"),
        "by_persona": group("persona"),
        "by_funnel_stage": group("funnel_stage"),
        "by_channel": group("channel"),
    }


@router.get("/{content_id}")
def get_content(
    content_id: str,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    row = conn.execute(
        "SELECT * FROM content_items WHERE id = %s", (content_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return dict(row)


@router.get("/{content_id}/similar")
def get_similar_content(
    content_id: str,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    row = conn.execute(
        "SELECT content_type, id FROM content_items WHERE id = %s",
        (content_id,),
    ).fetchone()
    if row is None:
        return []
    rows = conn.execute(
        """
        SELECT * FROM content_items
        WHERE content_type = %s AND id != %s
        ORDER BY updated_at DESC
        LIMIT 5
        """,
        (row["content_type"], content_id),
    ).fetchall()
    return [dict(item) for item in rows]
