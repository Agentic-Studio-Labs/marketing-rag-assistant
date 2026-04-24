# Content Intelligence Hub

Local-first macOS desktop app for searching, organizing, and repurposing marketing content.

The app uses an Electron + React frontend and a Python FastAPI sidecar. Content is stored in local SQLite, searched with FTS5 plus `sqlite-vss`, embedded locally with `sentence-transformers`, and repurposed with Anthropic models through LangGraph-based workflows.

## Current State

This repository is a working desktop rebuild of an earlier Streamlit app, but it is still in an "implemented core flows, some edges not wired" stage.

Implemented today:
- Dashboard with content stats and hybrid search
- Library view with filters, sorting, and content preview
- Content detail view with similar-content suggestions
- LangGraph repurposing flow for `linkedin`, `email`, `twitter`, and `summary`
- Generated-content browser for saved outputs
- Manual folder ingestion for local content files
- Settings UI for Anthropic key and watched-folder list

Partially implemented or not yet wired:
- The sidecar has an AI query/discovery endpoint, but the current UI does not use it
- Watched folders are saved, but automatic background watching is not currently connected at app startup
- Settings are written to SQLite, but startup does not currently reload them back into runtime config
- Frontend `vitest` is configured, but there are no frontend test files yet

## Architecture

- `electron/`: main-process app shell, menu, and Python sidecar lifecycle
- `src/`: React UI for dashboard, library, generated content, detail view, and settings
- `sidecar/`: FastAPI service, LangGraph agents, ingestion, storage, search, and providers
- `docs/plans/`: original design and implementation-plan documents

Main pieces:
- Electron starts the app window and attempts to spawn the Python sidecar
- React talks to the sidecar over `http://localhost:8420`
- SQLite stores source content, generated content, and app settings
- FTS5 handles keyword search; `sqlite-vss` handles vector similarity
- `sentence-transformers` creates local embeddings
- Anthropic powers the LLM-assisted query and repurpose flows

## Features

### Content ingestion

Supported file types:
- `.md`
- `.markdown`
- `.txt`
- `.pdf`
- `.docx`

Ingestion extracts text, infers a title, creates a local embedding, and upserts the record into SQLite.

### Search

The app supports:
- keyword search with FTS5
- vector similarity search with `sqlite-vss`
- hybrid scoring that merges both result sets

### Repurposing

The sidecar includes a LangGraph workflow that:
1. fetches a source item and similar content
2. analyzes the source
3. generates requested output formats
4. assigns lightweight quality scores

### Generated content

Generated outputs can be saved locally in SQLite and reviewed in the `Generated` view.

## Development Setup

### Requirements

- Node.js for Electron/React
- Python 3.12+ for the sidecar
- Anthropic API key for AI-powered repurposing and query features

### Install dependencies

```bash
npm install
cd sidecar
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running The App

### Option 1: Run the full desktop app

```bash
npm run dev
```

This starts the Electron app; the main process will try to start the Python sidecar automatically.

### Option 2: Run the sidecar directly

```bash
cd sidecar
source .venv/bin/activate
python3 -m uvicorn api:app --port 8420 --reload
```

Once the sidecar is running, you can start the Electron app separately with:

```bash
npm run dev
```

## Data And Configuration

By default, the sidecar stores local data in:

```text
~/Library/Application Support/ContentIntelligenceHub
```

That directory holds:
- `content.db`
- local embedding/model artifacts

Runtime config uses the `CIH_` prefix, for example:
- `CIH_PORT`
- `CIH_ANTHROPIC_API_KEY`

## Testing

Frontend:

```bash
npm test
```

Note: this is configured, but there are currently no frontend test files.

Sidecar:

```bash
cd sidecar
source .venv/bin/activate
python3 -m pytest
```

## Known Gaps

Compared with a fuller production-grade content pipeline, this repo does not yet include:
- web research and scraping integrations such as Tavily or Firecrawl
- image generation workflows
- Google Docs or Google Drive delivery
- client notifications
- LangGraph Cloud deployment
- LangSmith observability
- automatic watched-folder sync on app launch

## Reference Docs

- `CLAUDE.md`
- `docs/plans/2026-03-06-macos-app-design.md`
- `docs/plans/2026-03-06-macos-app-implementation.md`
