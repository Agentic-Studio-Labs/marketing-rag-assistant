from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import get_db, require_user
from shared.dispatch import dispatch_job
from shared.jobs import create_job, get_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


class RepurposeJobRequest(BaseModel):
    content_id: str
    formats: list[str] = Field(default_factory=list)
    tone: str = "professional"
    custom_instructions: dict[str, str] = Field(default_factory=dict)


class IngestJobRequest(BaseModel):
    object_paths: list[str] = Field(default_factory=list)
    source_label: str | None = None


@router.get("")
def api_list_jobs(
    job_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    items = list_jobs(conn, job_type=job_type, status=status)
    return {
        "items": items,
        "total": len(items),
        "limit": len(items),
        "offset": 0,
        "has_more": False,
    }


@router.get("/{job_id}")
def api_get_job(
    job_id: str,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    try:
        return get_job(conn, job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.post("/repurpose")
def api_create_repurpose_job(
    req: RepurposeJobRequest,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    job = create_job(
        conn,
        job_type="repurpose",
        payload=req.model_dump(),
        created_by=user["id"],
        source_content_id=req.content_id,
    )
    dispatch_job(conn, job["id"], "repurpose")
    return get_job(conn, job["id"])


@router.post("/ingest")
def api_create_ingest_job(
    req: IngestJobRequest,
    conn=Depends(get_db),
    user: dict = Depends(require_user),
):
    job = create_job(
        conn,
        job_type="ingest",
        payload=req.model_dump(),
        created_by=user["id"],
    )
    dispatch_job(conn, job["id"], "ingest")
    return get_job(conn, job["id"])
