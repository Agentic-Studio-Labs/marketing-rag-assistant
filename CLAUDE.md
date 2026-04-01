# Marketing RAG Assistant

Public portfolio name for this codebase: **local-first RAG over a curated content library** (Electron + React + FastAPI).  
Repository: [Agentic-Studio-Labs/marketing-rag-assistant](https://github.com/Agentic-Studio-Labs/marketing-rag-assistant).

## What "marketing" means here

The **RAG stack is domain-agnostic** (ingest → chunk → embed → retrieve → LLM). The marketing angle is mostly:

- **Data shape** — content types, persona, funnel stage, performance metadata on chunks.
- **Prompts / agents** — tuned for "content discovery" rather than e.g. financial coaching.

Swap corpus + filters + prompts and the same architecture applies to books, wikis, or support docs.

## What this is

A native-feeling macOS desktop app. Electron + React frontend with a Python FastAPI sidecar. Local-first: SQLite for storage and vector search (cosine similarity in Python), local **sentence-transformers** for embeddings, **Anthropic** for the LLM.

## Architecture

- **Electron** — window + spawns Python sidecar + macOS Keychain API key storage
- **React + TypeScript** — TailwindCSS, three tabs (Chat, Library, Audit)
- **FastAPI** sidecar — default `localhost:8420`
- **SQLite** — storage + audit log; cosine similarity in Python over stored embeddings
- **sentence-transformers** (all-MiniLM-L6-v2) — local embeddings
- **LLM** — provider interface; Anthropic in current wiring; token + cost tracking

### Features

- Chat with markdown-rendered answers, collapsible source citations, token/cost display
- Content Library with corpus stats, drag-and-drop upload (.md + .pdf), chunk preview
- Audit trail logging queries, uploads, reindexes, key changes, errors
- API key stored in macOS Keychain via Electron safeStorage

### Planned / next

- **sqlite-vss** — swap brute-force cosine for nearest-neighbor extension at scale
- **shadcn/ui** — component library for richer UI (data tables, dialogs)
- **LangGraph** — multi-step agent orchestration

## Dev workflow

```bash
# Terminal 1: Python sidecar
cd sidecar && python -m uvicorn api:app --port 8420 --reload

# Terminal 2: Electron + React dev
npm run dev

# Optional: packaged .app / .dmg in release/ — still needs venv in bundled sidecar; see README
npm run dist:mac
```

## Portfolio / publishing notes

- **Positioning** — describe this as a **portfolio project** or **reference implementation** (showcase of architecture and craft). Avoid calling it a "demo," which undersells depth.
- **First push to GitHub** — if you see `GH007` / email privacy errors, fix under GitHub **Settings → Emails** (allow the push or use your `users.noreply.github.com` address in `git config user.email`).

## Tech stack

- **Frontend**: Electron, React, TypeScript, TailwindCSS, react-markdown
- **Backend**: Python 3.12+, FastAPI, sentence-transformers, pymupdf, Anthropic
- **Testing**: Vitest (frontend), pytest (sidecar)

## Conventions

- TypeScript strict mode
- Python: type hints, pytest, ruff
- Prefer small, focused commits
