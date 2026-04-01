from __future__ import annotations

from pathlib import Path

from ingest import (
    _sections_from_body,
    iter_corpus_files,
    load_chunks,
    load_markdown_chunks,
    load_pdf_chunks,
)


def test_sections_split_on_headings() -> None:
    body = "Intro line.\n\n## First\nBody one.\n\n## Second\nBody two."
    sections = _sections_from_body(body)
    assert len(sections) == 3
    assert sections[0][0] is None
    assert "Intro" in sections[0][1]
    assert sections[1][0] == "First"
    assert sections[1][1] == "Body one."
    assert sections[2][0] == "Second"
    assert sections[2][1] == "Body two."


def test_sections_starting_with_heading() -> None:
    body = "## First\nBody one.\n\n## Second\nBody two."
    sections = _sections_from_body(body)
    assert len(sections) == 2
    assert sections[0][0] == "First"
    assert sections[0][1] == "Body one."
    assert sections[1][0] == "Second"
    assert sections[1][1] == "Body two."


def test_sections_no_headings() -> None:
    body = "Just a paragraph with no headings at all."
    sections = _sections_from_body(body)
    assert len(sections) == 1
    assert sections[0][0] is None
    assert "paragraph" in sections[0][1]


def test_load_markdown_resolves_source_path(tmp_path: Path) -> None:
    corpus = tmp_path / "sample_corpus"
    corpus.mkdir()
    md = corpus / "note.md"
    md.write_text(
        "---\ntitle: T\ncontent_type: x\n---\n\nPreamble.\n\n## A\nAlpha.\n",
        encoding="utf-8",
    )
    chunks = load_markdown_chunks(md, corpus)
    assert len(chunks) >= 2
    assert all(c["source_path"] == "sample_corpus/note.md" for c in chunks)


def test_load_pdf_chunks(tmp_path: Path) -> None:
    import fitz

    corpus = tmp_path / "sample_corpus"
    corpus.mkdir()
    pdf_path = corpus / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 100), "This is page one with enough text to pass the minimum.", fontsize=11
    )
    page.insert_text(
        (72, 120), "More content so the chunk is not skipped by the char threshold.", fontsize=11
    )
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text(
        (72, 100), "Page two has its own content for retrieval testing purposes here.", fontsize=11
    )
    page2.insert_text(
        (72, 120),
        "Additional lines to make sure we clear the minimum character limit.",
        fontsize=11,
    )
    doc.save(str(pdf_path))
    doc.close()

    chunks = load_pdf_chunks(pdf_path, corpus)
    assert len(chunks) == 2
    assert "page one" in chunks[0]["section_title"].lower()
    assert "page two" in chunks[1]["section_title"].lower()
    assert "page one" in chunks[0]["body"].lower()
    assert all(c["source_path"] == "sample_corpus/test.pdf" for c in chunks)


def test_load_chunks_dispatches_by_extension(tmp_path: Path) -> None:
    corpus = tmp_path / "sample_corpus"
    corpus.mkdir()
    md = corpus / "note.md"
    md.write_text("## Title\nBody text here.\n", encoding="utf-8")
    md_chunks = load_chunks(md, corpus)
    assert len(md_chunks) >= 1
    assert md_chunks[0]["section_title"] == "Title"


def test_iter_corpus_files_includes_pdf_and_md(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text("hello", encoding="utf-8")
    (corpus / "b.pdf").write_bytes(b"%PDF-1.4 fake")
    (corpus / "c.txt").write_text("ignored", encoding="utf-8")
    files = iter_corpus_files(corpus)
    names = [f.name for f in files]
    assert "a.md" in names
    assert "b.pdf" in names
    assert "c.txt" not in names
