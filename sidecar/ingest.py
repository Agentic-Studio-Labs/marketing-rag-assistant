from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta_block = parts[1].strip()
    body = parts[2].strip()
    meta: dict[str, str] = {}
    for line in meta_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower().replace(" ", "_")] = val.strip()
    return meta, body


def _sections_from_body(body: str) -> list[tuple[str | None, str]]:
    """Split on markdown ## headings; text before the first ## is an untitled preamble."""
    body = body.strip()
    if not body:
        return []
    if body.startswith("## "):
        body = "\n" + body
    parts = re.split(r"\n##\s+", body)
    if len(parts) == 1:
        return [(None, parts[0].strip())]
    out: list[tuple[str | None, str]] = []
    preamble = parts[0].strip()
    if preamble:
        out.append((None, preamble))
    for segment in parts[1:]:
        lines = segment.strip().split("\n", 1)
        title = lines[0].strip()
        text = lines[1].strip() if len(lines) > 1 else ""
        if text:
            out.append((title, text))
    return out


def load_markdown_chunks(path: Path, corpus_dir: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    rel = str(path.resolve().relative_to(corpus_dir.parent.resolve()))
    title_fallback = meta.get("title") or path.stem.replace("_", " ").title()

    chunks: list[dict[str, Any]] = []
    for section_title, text in _sections_from_body(body):
        chunks.append(
            {
                "source_path": rel,
                "section_title": section_title or title_fallback,
                "content_type": meta.get("content_type"),
                "persona": meta.get("persona"),
                "funnel_stage": meta.get("funnel_stage"),
                "body": text.strip(),
            }
        )
    return chunks


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

_MIN_CHUNK_CHARS = 80


def _clean_pdf_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_page_heading(text: str, stem: str, page_num: int) -> str:
    """Try to pull a chapter/section heading from the first line of page text."""
    fallback = f"{stem} — p.{page_num}"
    first_line = text.strip().split("\n", 1)[0].strip()
    if not first_line or len(first_line) > 120 or len(first_line) < 3:
        return fallback
    low = first_line.lower()
    if low.startswith(("chapter ", "section ", "part ")):
        return first_line
    if any(c.isalpha() for c in first_line) and len(first_line) <= 80:
        return first_line
    return fallback


def load_pdf_chunks(path: Path, corpus_dir: Path) -> list[dict[str, Any]]:
    """Extract text from a PDF, one chunk per page (skipping near-empty pages)."""
    import fitz  # pymupdf

    rel = str(path.resolve().relative_to(corpus_dir.parent.resolve()))
    doc = fitz.open(str(path))
    chunks: list[dict[str, Any]] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = _clean_pdf_text(page.get_text("text"))
        if len(text) < _MIN_CHUNK_CHARS:
            continue
        title = _extract_page_heading(text, path.stem, page_num + 1)
        chunks.append(
            {
                "source_path": rel,
                "section_title": title,
                "content_type": None,
                "persona": None,
                "funnel_stage": None,
                "body": text,
            }
        )

    doc.close()
    return chunks


# ---------------------------------------------------------------------------
# Corpus iteration
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {"*.md", "*.pdf"}


def iter_corpus_files(corpus_dir: Path) -> list[Path]:
    if not corpus_dir.is_dir():
        return []
    files: list[Path] = []
    for pattern in SUPPORTED_EXTENSIONS:
        files.extend(corpus_dir.glob(pattern))
    return sorted(files)


def load_chunks(path: Path, corpus_dir: Path) -> list[dict[str, Any]]:
    """Dispatch to the right loader based on file extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf_chunks(path, corpus_dir)
    return load_markdown_chunks(path, corpus_dir)
