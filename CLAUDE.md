# Content Intelligence Hub

## What this is

Marketing **content intelligence** for operators: search, library, detail views, **LangGraph repurposing**, and generated-output management.

**Primary direction:** **thin macOS client** (Electron + React) + **GCP backend** — Cloud Run API, Cloud Run worker, **Cloud SQL (Postgres)**, **GCS** artifacts, **Cloud Tasks**, **Secret Manager**, operator **magic-link** auth (OAuth/SSO later).

**Secondary / dev path:** **local FastAPI sidecar** on SQLite + FTS5 + sqlite-vss + local embeddings — useful for development and offline experimentation.

Public GitHub remote for CI: [`Agentic-Studio-Labs/content-intelligence-hub`](https://github.com/Agentic-Studio-Labs/content-intelligence-hub) (local folder name may differ).

**GCP production project:** `content-intel-hub-prod` (see `infra/gcp/AUTH.md`, `terraform.tfvars.example`).

**`main` branch protection:** pull requests required (0 approving reviews), **strict** status checks so **`node`** and **`python`** CI jobs must pass before merge, no force-push, admins included (`enforce_admins`). Ship work via feature branches → PR → merge.

## Repository map

| Area | Purpose |
|------|---------|
| `src/` | React UI, API client, auth, cloud/local runtime via `VITE_*` |
| `electron/` | Window, optional sidecar spawn; `CIH_USE_LOCAL_SIDECAR`, `CIH_API_BASE_URL` |
| `sidecar/` | Local FastAPI, agents, ingest, SQLite search/embeddings |
| `cloud/` | Control-plane API, worker app, Postgres, GCS, task enqueue |
| `infra/gcp/` | Terraform for GCP resources |

**Cloud hardening (summary):** worker verifies **Cloud Tasks OIDC** on job endpoints; **`CIH_CLOUD_ENVIRONMENT=production`** rejects dev crypto defaults and `SKIP_WORKER_OIDC`; CORS is env-driven; Terraform defaults include **GCS public access prevention**, **SQL `ENCRYPTED_ONLY`**, optional **Run invoker** binding for the tasks SA only (`infra/gcp/README.md`).

## Current product surface

- Dashboard, library, content detail + similar content, generated library, settings.
- **Cloud:** session/magic-link, jobs for repurpose/ingest, uploads to GCS, metadata in Postgres.
- **Local sidecar:** hybrid search, file ingest, repurpose against SQLite.

## Gaps / caveats

- Dashboard uses **`/api/agents/query`** (via `api.discover`) when **`VITE_API_MODE` is not `cloud`**; cloud mode still uses **`/api/content/search`**.
- Watched folders + background watcher not fully wired at startup (local settings story).
- Production hardening (SQL access pattern, OAuth) is incremental.

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
