# GCP Infrastructure

Terraform module for the Content Intelligence Hub cloud backend: Cloud SQL, GCS, Cloud Tasks, Secret Manager + IAM.

**Cloud Run is intentionally NOT managed here.** The production services **`cih-api-prod`** and **`cih-worker-prod`** are deployed via **`gcloud run deploy`** + **`cloud/cloudbuild.*.yaml`**, and carry rich runtime config (env vars, secret mounts, Cloud SQL connector, tasks-invoker SA). Modeling that in Terraform is a separate, bigger effort; for now the deploy tool owns the Run services and this module stays focused on the durable infra (database, bucket, queue, secrets).

**Local gcloud / Terraform auth:** see [AUTH.md](./AUTH.md) (named `cih` config, ADC, optional SA impersonation).

## Hardening defaults (this module)

| Area | Behavior |
|------|----------|
| **GCS** | Uniform bucket access + **public access prevention enforced** |
| **Cloud SQL** | **`ssl_mode = ENCRYPTED_ONLY`** by default; backups optional; deletion protection off by default (toggle for prod) |
| **Public SQL IP** | **`db_public_ipv4_enabled`** defaults true for simple dev; set **false** and use private networking / connector when ready |

The API service (`cih-api-prod`) is a **public** Cloud Run URL (magic-link and desktop client). Restrict CORS with **`CIH_CLOUD_CORS_ALLOW_ORIGINS`** on the service itself.

## Resend (magic-link email)

1. Create a Secret Manager secret and store the Resend API key (Console or `gcloud`).
2. In **`terraform.tfvars`**, set **`resend_secret_id`** to that secret's **short id** (not the env var name `CIH_CLOUD_RESEND_API_KEY`).
3. Run **`terraform apply`**. This adds **`roles/secretmanager.secretAccessor`** on that secret for the **cih-api-prod** runtime service account (default: **`PROJECT_NUMBER-compute@developer.gserviceaccount.com`**, or override with **`cloud_run_api_service_account_email`** if the service uses a custom SA).
4. In **Cloud Run → cih-api-prod**, mount the secret as environment variable **`CIH_CLOUD_RESEND_API_KEY`**:

   ```bash
   gcloud run services update cih-api-prod \
     --region=us-central1 --project=content-intel-hub-prod \
     --update-secrets=CIH_CLOUD_RESEND_API_KEY=CIH_CLOUD_RESEND_API_KEY:latest
   ```

## Application guardrails (`cloud/shared/config.py`)

- **`CIH_CLOUD_ENVIRONMENT=production`**: rejects default magic-link/session secrets and rejects **`CIH_CLOUD_SKIP_WORKER_OIDC=true`**.
- **Worker**: verifies **Cloud Tasks OIDC** JWT on `POST /tasks/jobs/{id}` unless **`CIH_CLOUD_SKIP_WORKER_OIDC=true`** (local debugging only).

## Usage

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars   # edit if needed; tfvars is gitignored
terraform init
terraform plan
```

## Cloud Run deploys (out-of-band)

Terraform does not manage the Run services. Build + deploy with Cloud Build:

```bash
# Build + push an API image
gcloud builds submit \
  --config=cloud/cloudbuild.api.yaml \
  --substitutions=_IMAGE=us-central1-docker.pkg.dev/content-intel-hub-prod/cloud-run-source-deploy/cih-api:live \
  --project=content-intel-hub-prod .

# Deploy to cih-api-prod (preserves existing env + secret mounts)
gcloud run deploy cih-api-prod \
  --image=us-central1-docker.pkg.dev/content-intel-hub-prod/cloud-run-source-deploy/cih-api:live \
  --region=us-central1 --project=content-intel-hub-prod
```

Same pattern for `cloudbuild.worker.yaml` → `cih-worker-prod`.

## Partial apply / common errors

### `409 Queue already exists`

The queue **`tasks_queue_name`** (default **`cih-job-queue`**) is already in the project. Either:

- **Import** it into state (region must match **`var.region`**):

  ```bash
  terraform import 'google_cloud_tasks_queue.jobs[0]' \
    "projects/PROJECT_ID/locations/REGION/queues/QUEUE_NAME"
  ```

  Example: `projects/content-intel-hub-prod/locations/us-central1/queues/cih-job-queue`

- **Or** set **`manage_cloud_tasks_queue = false`** in **`terraform.tfvars`** so Terraform does not try to create the queue.

## Legacy note

V1 files were minimal; re-run **`terraform plan`** before apply — SQL **`ssl_mode`** and bucket **PAP** may update existing resources.
