"""Edge-case tests for the hierarchical chunker."""
from __future__ import annotations
import pytest
from docintel.processing.chunker import HierarchicalChunker


@pytest.fixture
def chunker():
    return HierarchicalChunker(chunk_size=20, chunk_overlap=0, min_chunk_size=0)


def test_empty_text_returns_no_chunks(chunker):
    assert chunker.chunk("") == []


def test_whitespace_only_returns_no_chunks(chunker):
    assert chunker.chunk("   \n\n   ") == []


def test_short_lowercase_text_produces_one_chunk(chunker):
    # "hello" doesn't match any heading pattern, so it becomes content
    chunks = chunker.chunk("hello", doc_path="x.txt", page=1)
    assert len(chunks) == 1
    assert chunks[0].text == "hello"
    assert chunks[0].metadata["page"] == 1


def test_plain_paragraphs_no_headings(chunker):
    text = "First paragraph with some words.\n\nSecond paragraph here."
    chunks = chunker.chunk(text, doc_path="plain.txt")
    assert len(chunks) >= 1
    combined = " ".join(c.text for c in chunks)
    assert "First paragraph" in combined


def test_heading_only_no_body_produces_no_chunks(chunker):
    # A heading with nothing beneath it generates nothing
    chunks = chunker.chunk("# Title Only", doc_path="empty.md")
    assert chunks == []


def test_unicode_text_preserved(chunker):
    text = "Révision du moteur\n\nLe moteur électrique fonctionne à 230 V."
    chunks = chunker.chunk(text, doc_path="fr.txt")
    assert len(chunks) >= 1
    assert "électrique" in chunks[0].text


def test_very_long_line_splits_into_multiple_chunks():
    chunker = HierarchicalChunker(chunk_size=5, chunk_overlap=0, min_chunk_size=0)
    text = " ".join(f"word{i}" for i in range(30))
    chunks = chunker.chunk(text, doc_path="long.txt")
    assert len(chunks) > 1


def test_doc_summary_prepended_to_embed_text(chunker):
    chunks = chunker.chunk("Some text content.", doc_summary="A great summary.")
    assert chunks[0].metadata["_embed_text"].startswith("[Document: A great summary.]")


def test_markdown_depth_tracked_in_breadcrumb(chunker):
    text = "# Chapter\n\nIntro\n\n## Section\n\nDetails here."
    chunks = chunker.chunk(text, doc_path="manual.md")
    breadcrumbs = [c.metadata["breadcrumb"] for c in chunks]
    assert any("Chapter" in b for b in breadcrumbs)
    assert any("Section" in b for b in breadcrumbs)


def test_min_chunk_size_filters_small_chunks():
    chunker = HierarchicalChunker(chunk_size=10, chunk_overlap=0, min_chunk_size=40)
    chunks = chunker.chunk("Tiny.", doc_path="x.txt")
    assert chunks == []
