# Content Intelligence Hub - macOS App

## What This Is

A native-feeling macOS desktop app for marketing content intelligence. Electron + React frontend with a Python FastAPI sidecar backend. Local-first: SQLite + sqlite-vss for storage, local sentence-transformers for embeddings, Anthropic API for LLM.

## Current Product Surface

Implemented in the current repo:
- Dashboard with stats and hybrid search
- Library view with filters, sorting, and preview
- Content detail view with similar-content lookup
- LangGraph repurposing flow for `linkedin`, `email`, `twitter`, and `summary`
- Generated-content browser
- Settings for Anthropic API key and watched folders
- Manual file/folder ingestion for local content

Current gaps / caveats:
- `/api/agents/query` exists, but the current UI does not call it
- Watched folders are stored in settings, but background file watching is not wired into startup flow
- Settings are persisted to SQLite, but not reloaded from SQLite during startup
- Frontend `vitest` is configured, but there are no frontend test files yet

## Architecture

- **Electron** main process manages window + spawns Python sidecar
- **React + TypeScript** frontend with TailwindCSS + shadcn/ui
- **Python FastAPI** sidecar on localhost:8420
- **SQLite + sqlite-vss** for content storage and vector search
- **sentence-transformers** (all-MiniLM-L6-v2, ONNX) for local embeddings
- **Anthropic Claude API** for LLM features (provider-abstracted for future local LLM support)

## Key Design Docs

- `docs/plans/2026-03-06-macos-app-design.md` — full architecture design

## Prior Art

This app is a desktop rebuild of a Streamlit web app (see `/Users/jm/Projects/Content-Intelligence-Hub-Demo/`). Port agent logic and search functions from that codebase's `src/` directory.

## Dev Workflow

```bash
# One-time sidecar setup
cd sidecar
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run sidecar directly when needed
python3 -m uvicorn api:app --port 8420 --reload

# Electron + React dev
cd ..
npm run dev
```

Notes:
- `npm run dev` starts the Electron app and the Electron main process will try to start the sidecar automatically
- The sidecar defaults to `http://localhost:8420`
- Local app data lives under `~/Library/Application Support/ContentIntelligenceHub`

## Tech Stack

- **Frontend**: Electron, React, TypeScript, TailwindCSS, shadcn/ui, @tanstack/react-table
- **Backend**: Python 3.12+, FastAPI, LangGraph, Anthropic SDK, sentence-transformers, sqlite-vss
- **Packaging**: electron-builder, PyInstaller/python-build-standalone
- **Testing**: Vitest (frontend), pytest (sidecar)

## Conventions

- TypeScript strict mode
- Python: type hints, pytest, ruff
- Prefer editing existing files over creating new ones
- Small, focused, atomic commits

## Testing

```bash
# Frontend
npm test

# Sidecar
cd sidecar
source .venv/bin/activate
python3 -m pytest
```

Notes:
- `npm test` is configured, but currently reports no frontend test files
- Sidecar tests require the sidecar dev dependencies to be installed into the virtualenv
