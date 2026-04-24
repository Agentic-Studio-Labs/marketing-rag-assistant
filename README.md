# Content Intelligence Hub

macOS desktop app for searching, organizing, and repurposing marketing content. The **default product direction** is a **thin Electron + React client** backed by a **GCP control plane**; a **local Python sidecar** remains available for development and offline-style use.

## Architecture (two modes)

### Cloud (target / production-shaped)

- **`cloud/`** — FastAPI control-plane API on **Cloud Run** (sessions, content metadata, jobs, uploads, integrations).
- **Cloud SQL (PostgreSQL)** — relational metadata (users, workspaces, content rows, jobs, integration state).
- **Google Cloud Storage** — workspace-scoped object storage for uploads and generated artifacts.
- **Cloud Tasks** — async handoff to a separate **Cloud Run worker** that runs LangGraph repurpose and ingest pipelines.
- **Secret Manager** — provider secrets (e.g. Anthropic); magic-link and session signing secrets in env/Secret Manager for production.
- **Identity** — operator **magic-link** auth first; OAuth/SSO is a planned upgrade.
- **`infra/gcp/`** — Terraform sketch for buckets, SQL, queues, services (adjust to your project).

The desktop app talks to the API over HTTPS; build-time **`VITE_*`** and Electron **`CIH_API_BASE_URL`** / **`CIH_USE_LOCAL_SIDECAR`** select this mode (see `.env.example`).

### Local sidecar (development / local-first)

- **`sidecar/`** — FastAPI on **localhost:8420**, **SQLite** + FTS5 + **sqlite-vss**, **sentence-transformers** embeddings, LangGraph repurpose flows, Anthropic via env API key.
- **`electron/`** — can spawn the sidecar automatically when pointed at local base URL.

## Current state

**Implemented**

- Dashboard, library, content detail (similar content), generated-content browser, settings.
- Cloud path: authenticated API client, magic-link login, job-based repurpose, GCS-backed uploads/ingest (see `cloud/`).
- Local path: hybrid search, ingestion, repurpose against SQLite.

**Still rough or incomplete**

- **Local** dashboard search calls sidecar **`/api/agents/query`** (`api.discover`); **cloud** mode uses **`/api/content/search`**.
- Watched-folder background watching is not fully wired to app startup.
- Local settings reload from SQLite on startup is incomplete for some paths.
- Hardening (e.g. private connectivity for Cloud SQL in non-dev) is ongoing.

## Repository layout

| Path | Role |
|------|------|
| `src/` | React UI |
| `electron/` | Main process, optional sidecar spawn, cloud base URL |
| `sidecar/` | Local FastAPI + agents + SQLite |
| `cloud/` | Cloud Run API, shared libs, worker service |
| `infra/gcp/` | Terraform for GCP resources |
| `docs/plans/` | Design and implementation notes |

## Features (summary)

- **Ingestion**: markdown, text, PDF, docx — local sidecar writes to SQLite; cloud worker writes to Postgres + GCS.
- **Search**: FTS + vector + hybrid (local); cloud exposes search/metadata APIs backed by Postgres (and embeddings in the worker path).
- **Repurpose**: LangGraph pipeline (formats `linkedin`, `email`, `twitter`, `summary`) — runs in sidecar locally or in the Cloud Run worker.

## Development setup

**Requirements:** Node.js 22+, Python 3.12+, Anthropic access for AI features. For cloud work you also need a GCP project and deployed API/worker or emulated config.

```bash
npm install
cd sidecar
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy **`.env.example`** to `.env` and adjust for either local sidecar or cloud API URLs.

### Run desktop against **local** sidecar

```bash
npm run dev
```

Ensure the app is using `http://localhost:8420` (default). Electron starts the sidecar unless `CIH_USE_LOCAL_SIDECAR=false` and a remote `CIH_API_BASE_URL` is set.

### Run desktop against **cloud** API

Set (see `.env.example`):

- `CIH_USE_LOCAL_SIDECAR=false`
- `CIH_API_BASE_URL=https://<your-cloud-run-api>`
- Build/run renderer with matching `VITE_API_BASE_URL`, `VITE_REQUIRE_AUTH=true`, `VITE_API_MODE=cloud` as needed.

### Run sidecar only

```bash
cd sidecar
source .venv/bin/activate
python3 -m uvicorn api:app --port 8420 --reload
```

## Data and configuration

**Local sidecar** defaults to:

`~/Library/Application Support/ContentIntelligenceHub` — `content.db`, models cache.

Env prefix **`CIH_`** for sidecar (see `sidecar/config.py`).

**Cloud** uses prefix **`CIH_CLOUD_`** (see `cloud/shared/config.py`) — DB, bucket, queue, worker URL, secrets.

## Testing

```bash
npm test          # Vitest (renderer)
cd sidecar && source .venv/bin/activate && python3 -m pytest   # Sidecar
```

CI (GitHub Actions on this repo): Node build + Vitest + sidecar pytest.

## Known gaps (product / infra)

- Web research integrations (Tavily, Firecrawl, etc.), image gen, Google Docs/Drive delivery, client notifications.
- OAuth/SSO (magic-link is the current operator auth).
- Full production hardening: least-privilege IAM, SQL connectivity choices, observability dashboards.

## Reference

- `CLAUDE.md` — contributor / agent context
- `.env.example` — env vars for local vs cloud
- `docs/plans/` — historical design docs
