from shared.config import settings
from shared.tasks import enqueue_job_task
from shared.jobs import update_job_status


def dispatch_job(conn, job_id: str, job_type: str) -> None:
    if settings.queue_mode == "tasks":
        enqueue_job_task(job_id, job_type)
        return

    if settings.queue_mode != "inline":
        return

    try:
        if job_type == "repurpose":
            from workers.repurpose_worker import process_repurpose_job

            process_repurpose_job(conn, job_id)
        elif job_type == "ingest":
            from workers.ingest_worker import process_ingest_job

            process_ingest_job(conn, job_id)
    except Exception as exc:
        update_job_status(conn, job_id, status="failed", error=str(exc))
