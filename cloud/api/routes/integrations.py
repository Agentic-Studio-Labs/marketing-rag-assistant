from fastapi import APIRouter, Depends

from api.deps import get_db, require_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
def list_integrations(
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    rows = conn.execute(
        """
        SELECT id, provider, connected, last_checked_at, last_rotated_at, status_message
        FROM integration_states
        ORDER BY provider
        """
    ).fetchall()
    return [dict(row) for row in rows]
