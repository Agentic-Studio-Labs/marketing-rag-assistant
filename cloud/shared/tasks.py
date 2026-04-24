import json

from google.cloud import tasks_v2

from shared.config import settings


def enqueue_job_task(job_id: str, job_type: str) -> None:
    if not settings.worker_url:
        raise RuntimeError("CIH_CLOUD_WORKER_URL is not configured")
    if not settings.tasks_service_account_email:
        raise RuntimeError("CIH_CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL is not configured")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.gcp_project_id,
        settings.tasks_location,
        settings.tasks_queue,
    )
    url = f"{settings.worker_url.rstrip('/')}/tasks/jobs/{job_id}"
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"job_type": job_type}).encode("utf-8"),
            "oidc_token": {
                "service_account_email": settings.tasks_service_account_email,
                "audience": settings.worker_url.rstrip("/"),
            },
        }
    }
    client.create_task(parent=parent, task=task)
