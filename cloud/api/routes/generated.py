from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_db, require_user

router = APIRouter(prefix="/api/generated", tags=["generated"])


@router.get("")
def list_generated(
    format: str | None = Query(default=None),
    tone: str | None = Query(default=None),
    limit: int = Query(default=50),
    offset: int = Query(default=0),
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    clauses = ["1=1"]
    params: list[object] = []
    if format:
        clauses.append("format = %s")
        params.append(format)
    if tone:
        clauses.append("tone = %s")
        params.append(tone)

    total = conn.execute(
        f"SELECT COUNT(*) AS count FROM generated_items WHERE {' AND '.join(clauses)}",
        tuple(params),
    ).fetchone()["count"]
    rows = conn.execute(
        f"""
        SELECT * FROM generated_items
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC
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


@router.get("/{generated_id}")
def get_generated(
    generated_id: str,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    row = conn.execute(
        "SELECT * FROM generated_items WHERE id = %s", (generated_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Generated content not found")
    return dict(row)
