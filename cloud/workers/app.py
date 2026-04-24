from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from shared.db import close_pool, managed_connection, open_pool
from workers.ingest_worker import process_ingest_job
from workers.repurpose_worker import process_repurpose_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(title="Content Intelligence Hub Worker", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "mode": "worker"}


@app.post("/tasks/jobs/{job_id}")
def process_job(job_id: str, body: dict):
    job_type = body.get("job_type")
    with managed_connection() as conn:
        if job_type == "repurpose":
            return process_repurpose_job(conn, job_id)
        if job_type == "ingest":
            return process_ingest_job(conn, job_id)
        raise HTTPException(status_code=400, detail=f"Unsupported job type: {job_type}")
