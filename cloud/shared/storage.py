import tempfile
from datetime import datetime, UTC
from pathlib import Path
import re
import uuid

from shared.config import settings


def _strip_gcs_uri(object_path: str) -> str:
    if object_path.startswith("gs://"):
        prefix = f"gs://{settings.artifact_bucket}/"
        if object_path.startswith(prefix):
            return object_path.removeprefix(prefix)
        return object_path.split("/", 3)[-1]
    return object_path


def normalize_object_path(object_path: str) -> str:
    return _strip_gcs_uri(object_path).lstrip("/").replace("..", "")


def sanitize_object_path(object_path: str) -> Path:
    return settings.object_root / normalize_object_path(object_path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def object_uri(object_path: str) -> str:
    normalized_path = normalize_object_path(object_path)
    if settings.artifact_bucket:
        return f"gs://{settings.artifact_bucket}/{normalized_path}"
    return str(sanitize_object_path(normalized_path))


def _slugify_filename(file_name: str) -> str:
    file_name = Path(file_name).name.strip() or "upload.bin"
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(file_name).stem).strip("-") or "upload"
    suffix = Path(file_name).suffix.lower()
    return f"{stem}{suffix}"


def workspace_prefix(workspace_id: str | None) -> str:
    return f"workspaces/{workspace_id or 'default'}"


def build_upload_object_path(
    workspace_id: str | None, file_name: str, now: datetime | None = None
) -> str:
    current = now or datetime.now(UTC)
    date_prefix = current.strftime("%Y/%m/%d")
    upload_id = f"{current.strftime('%H%M%S')}-{uuid.uuid4()}"
    return (
        f"{workspace_prefix(workspace_id)}/uploads/{date_prefix}/"
        f"{upload_id}/{_slugify_filename(file_name)}"
    )


def build_normalized_object_path(
    workspace_id: str | None, job_id: str, file_name: str
) -> str:
    safe_name = _slugify_filename(file_name)
    return f"{workspace_prefix(workspace_id)}/normalized/{job_id}/{safe_name}"


def build_generated_object_path(
    workspace_id: str | None, job_id: str, file_name: str
) -> str:
    safe_name = _slugify_filename(file_name)
    return f"{workspace_prefix(workspace_id)}/generated/{job_id}/{safe_name}"


def _gcs_client():
    from google.cloud import storage

    project = settings.gcp_project_id or None
    return storage.Client(project=project)


def _bucket():
    return _gcs_client().bucket(settings.artifact_bucket)


def object_exists(object_path: str) -> bool:
    if settings.artifact_bucket:
        return _bucket().blob(normalize_object_path(object_path)).exists()
    return sanitize_object_path(object_path).exists()


def write_object(object_path: str, data: bytes) -> str:
    normalized_path = normalize_object_path(object_path)
    if settings.artifact_bucket:
        blob = _bucket().blob(normalized_path)
        blob.upload_from_string(data)
        return object_uri(normalized_path)

    path = sanitize_object_path(normalized_path)
    ensure_parent(path)
    path.write_bytes(data)
    return str(path)


def read_object_text(object_path: str) -> str:
    normalized_path = normalize_object_path(object_path)
    if settings.artifact_bucket:
        return _bucket().blob(normalized_path).download_as_text()
    path = sanitize_object_path(normalized_path)
    return path.read_text(encoding="utf-8")


def read_object_bytes(object_path: str) -> bytes:
    normalized_path = normalize_object_path(object_path)
    if settings.artifact_bucket:
        return _bucket().blob(normalized_path).download_as_bytes()
    return sanitize_object_path(normalized_path).read_bytes()


def materialize_object(object_path: str) -> Path:
    data = read_object_bytes(object_path)
    suffix = Path(normalize_object_path(object_path)).suffix
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(data)
    handle.flush()
    handle.close()
    return Path(handle.name)
