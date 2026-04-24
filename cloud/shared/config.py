from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIH_CLOUD_", extra="ignore")

    environment: str = "development"
    port: int = 8484
    data_dir: Path = Path(__file__).resolve().parents[1] / ".data"
    storage_dir: Path | None = None

    magic_link_secret: str = "dev-magic-link-secret"
    session_secret: str = "dev-session-secret"
    session_ttl_hours: int = 24
    magic_link_ttl_minutes: int = 15

    default_workspace_name: str = "Default Workspace"
    allowed_email_domains: str = "*"

    auth_mode: str = "magic_link"
    upload_mode: str = "cloud"

    anthropic_api_key: str = ""
    anthropic_secret_ref: str = "anthropic_primary"
    llm_model: str = "claude-sonnet-4-6"
    artifact_bucket: str = ""
    queue_mode: str = "inline"
    gcp_project_id: str = ""
    db_name: str = "cih"
    db_user: str = "cih_app"
    db_password: str = ""
    db_host: str = ""
    db_port: int = 5432
    cloudsql_instance_connection_name: str = ""
    db_pool_min_size: int = 1
    db_pool_max_size: int = 4
    tasks_queue: str = "cih-job-queue"
    tasks_location: str = "us-central1"
    worker_url: str = ""
    tasks_service_account_email: str = ""
    worker_timeout_seconds: int = 3600

    cors_allow_origins: str = "*"
    worker_oidc_audience: str = ""
    skip_worker_oidc: bool = False

    @property
    def db_host_path(self) -> str:
        if self.db_host:
            return self.db_host
        if self.cloudsql_instance_connection_name:
            return f"/cloudsql/{self.cloudsql_instance_connection_name}"
        return ""

    @property
    def object_root(self) -> Path:
        return self.storage_dir or (self.data_dir / "objects")

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.object_root.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def cors_origins_list(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @model_validator(mode="after")
    def production_guardrails(self):
        env = self.environment.lower()
        if env not in ("production", "prod"):
            return self
        if self.magic_link_secret == "dev-magic-link-secret":
            raise ValueError(
                "CIH_CLOUD_MAGIC_LINK_SECRET must not use the dev default when CIH_CLOUD_ENVIRONMENT=production",
            )
        if self.session_secret == "dev-session-secret":
            raise ValueError(
                "CIH_CLOUD_SESSION_SECRET must not use the dev default when CIH_CLOUD_ENVIRONMENT=production",
            )
        if self.skip_worker_oidc:
            raise ValueError(
                "CIH_CLOUD_SKIP_WORKER_OIDC must be false when CIH_CLOUD_ENVIRONMENT=production",
            )
        return self


settings = Settings()
