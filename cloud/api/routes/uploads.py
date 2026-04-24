from datetime import datetime, UTC

from fastapi import APIRouter, Body, Depends
from fastapi.responses import Response

from api.deps import get_db, require_user
from shared.storage import build_upload_object_path, write_object

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/init")
def init_upload(
    body=Body(...),
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    object_path = build_upload_object_path(
        user.get("workspace_id"),
        body["file_name"],
        datetime.now(UTC),
    )
    return {
        "object_path": object_path,
        "upload_url": f"/uploads/dev/{object_path}",
    }


@router.put("/dev/{object_path:path}")
def dev_upload(
    object_path: str, payload: bytes = Body(..., media_type="application/octet-stream")
):
    write_object(object_path, payload)
    return Response(status_code=204)
