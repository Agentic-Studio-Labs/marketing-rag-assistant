# Content Intelligence Hub

## What this is

Marketing **content intelligence** for operators: search, library, detail views, **LangGraph repurposing**, and generated-output management.

**Primary direction:** **thin macOS client** (Electron + React) + **GCP backend** — Cloud Run API, Cloud Run worker, **Cloud SQL (Postgres)**, **GCS** artifacts, **Cloud Tasks**, **Secret Manager**, operator **magic-link** auth (OAuth/SSO later).

**Secondary / dev path:** **local FastAPI sidecar** on SQLite + FTS5 + sqlite-vss + local embeddings — useful for development and offline experimentation.

Public GitHub remote for CI: [`Agentic-Studio-Labs/content-intelligence-hub`](https://github.com/Agentic-Studio-Labs/content-intelligence-hub) (local folder name may differ).

**GCP production project:** `content-intel-hub-prod` (project number `393636347048`; see `infra/gcp/AUTH.md`, `terraform.tfvars.example`). **Local Terraform vars** live in `infra/gcp/terraform.tfvars` (gitignored—copy from `terraform.tfvars.example`).

**`main` branch protection:** pull requests required (0 approving reviews), **strict** status checks so **`node`** and **`python`** CI jobs must pass before merge, no force-push, admins included (`enforce_admins`). Ship work via feature branches → PR → merge.

## Repository map

| Area | Purpose |
|------|---------|
| `src/` | React UI, API client, auth, cloud/local runtime via `VITE_*` |
| `electron/` | Window, optional sidecar spawn; `CIH_USE_LOCAL_SIDECAR`, `CIH_API_BASE_URL` |
| `sidecar/` | Local FastAPI, agents, ingest, SQLite search/embeddings |
| `cloud/` | Control-plane API, worker app, Postgres, GCS, task enqueue |
| `infra/gcp/` | Terraform for GCP resources + **partial-apply recovery** (`README.md`: Tasks 409, missing Run images, bootstrap images) |

**Cloud hardening (summary):** worker verifies **Cloud Tasks OIDC** on job endpoints; **`CIH_CLOUD_ENVIRONMENT=production`** rejects dev crypto defaults and `SKIP_WORKER_OIDC`; CORS is env-driven; Terraform defaults include **GCS public access prevention**, **SQL `ENCRYPTED_ONLY`**, optional **Run invoker** binding for the tasks SA only (`infra/gcp/README.md`).

## Current product surface

- Dashboard, library, content detail + similar content, generated library, settings.
- **Cloud:** session/magic-link, jobs for repurpose/ingest, uploads to GCS, metadata in Postgres.
- **Local sidecar:** hybrid search, file ingest, repurpose against SQLite.

## Gaps / caveats

- Dashboard home search uses **`POST /api/agents/query`** (`api.discover`) in **local and cloud** (cloud: Postgres keyword search + Anthropic; local: hybrid FTS + embeddings + Anthropic). **`POST /api/content/search`** remains for simple keyword-only use.
- **Local sidecar:** `watched_folders` are loaded from SQLite on startup; **`ContentWatcher`** (watchdog) ingests supported files on create/modify; **`PUT /api/settings`** restarts the watcher when folders change (`sidecar/api.py`, `sidecar/watcher.py`).
- Production hardening (SQL access pattern, OAuth) is incremental.
- **Magic link (cloud):** emails are normalized (case/trim); **`POST /auth/magic-link/start`** returns a generic **`{ status, email }`** for unknown/disallowed addresses (no user enumeration); **`dev_magic_link_token`** is only included when **`CIH_CLOUD_ENVIRONMENT`** is not **`production`** / **`prod`**. With **`CIH_CLOUD_RESEND_API_KEY`**, the API sends mail via **Resend** from **`CIH_CLOUD_MAGIC_LINK_FROM_EMAIL`** (default **noreply@agenticstudiolabs.com**); optional **`CIH_CLOUD_MAGIC_LINK_APP_BASE_URL`** adds a **`#/login?token=...`** button link. Response may include **`delivery`**: `email` or `email_failed`. Rate limit: **`CIH_CLOUD_MAGIC_LINK_MAX_STARTS_PER_EMAIL_PER_HOUR`** (default 15). Login UI reads **`token`** / **`magic_token`** in the hash query.
- **Resend + Secret Manager (prod):** verified sending domain **agenticstudiolabs.com**. Secret Manager secret id **`CIH_CLOUD_RESEND_API_KEY`** holds the Resend API key. Terraform (when **`resend_secret_id`** is set) grants **`roles/secretmanager.secretAccessor`** to the **cih-api** runtime SA (default **`PROJECT_NUMBER-compute@developer.gserviceaccount.com`**). **Cloud Run must still mount** that secret as env **`CIH_CLOUD_RESEND_API_KEY`**—IAM alone does not inject env vars.
- **Terraform / GCP apply (Apr 2026 handoff):** A full apply created **Cloud SQL** `cih-cloud-sql`, GCS **`cih-artifacts-dev`**, empty **`anthropic-primary`** secret, and **Resend IAM**. It **failed** on: **Cloud Tasks** `409` queue already exists (**`cih-job-queue`**), and **Cloud Run** images **`us-docker.pkg.dev/content-intel-hub-prod/cih/cih-api|worker:latest`** not in Artifact Registry. **Fix:** import queue (`terraform import 'google_cloud_tasks_queue.jobs[0]' 'projects/…/locations/us-central1/queues/cih-job-queue'`) **or** **`manage_cloud_tasks_queue = false`**; **build/push** Docker images (`cloud/Dockerfile.api`, `cloud/Dockerfile.worker`) **or** temporary **`gcr.io/cloudrun/hello`** overrides per `infra/gcp/README.md`. Feature branch **`feat/resend-magic-link-email`** — land via PR (e.g. **#10**).

## Dev workflow

**Local sidecar**

```bash
cd sidecar && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
python3 -m uvicorn api:app --port 8420 --reload
# from repo root
npm run dev
```

Data default: `~/Library/Application Support/ContentIntelligenceHub`. Env: **`CIH_`**.

**Cloud-oriented desktop** — set `CIH_USE_LOCAL_SIDECAR=false`, cloud `CIH_API_BASE_URL`, and matching **`VITE_API_BASE_URL`**, **`VITE_REQUIRE_AUTH`**, **`VITE_API_MODE=cloud`**. Cloud services use **`CIH_CLOUD_`** (see `cloud/shared/config.py`). See **`.env.example`**.

## Tech stack

- **Frontend:** Electron, React, TypeScript, Tailwind, shadcn/ui, TanStack Table, Vitest.
- **Local backend:** Python 3.12+, FastAPI, LangGraph, Anthropic, sentence-transformers, sqlite-vss.
- **Cloud backend:** FastAPI, psycopg, GCS client, Cloud Tasks, workers share LangGraph repurpose/ingest logic with sidecar patterns.

## Conventions

- TypeScript strict; Python type hints, pytest, ruff.
- Prefer small, focused edits; match existing style.
- Do not commit `.env` or secrets.

## Testing

```bash
npm test
cd sidecar && source .venv/bin/activate && python3 -m pytest
```

## Design history

- `docs/plans/2026-03-06-macos-app-design.md`
- Legacy RAG-only snapshot (unrelated root): branch `archive/marketing-rag-assistant-main` on the same remote if ever needed.
