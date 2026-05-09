import pytest

from docintel.processing.chunker import HierarchicalChunker


def test_chunker_rejects_overlap_equal_to_size() -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        HierarchicalChunker(chunk_size=10, chunk_overlap=10)


def test_chunker_adds_page_and_breadcrumb_metadata() -> None:
    text = "# Pump Manual\n\nDaily inspection requires checking pressure and seals."
    chunker = HierarchicalChunker(chunk_size=50, chunk_overlap=0, min_chunk_size=0)

    chunks = chunker.chunk(text, doc_path="manual.md", page=3)

    assert len(chunks) == 1
    assert chunks[0].metadata["breadcrumb"] == "Pump Manual"
    assert chunks[0].metadata["page"] == 3


def test_chunker_uses_doc_summary_for_embedding_text() -> None:
    chunker = HierarchicalChunker(chunk_size=50, chunk_overlap=0, min_chunk_size=0)

    chunks = chunker.chunk("A useful paragraph for retrieval.", doc_summary="Hydraulic system.")

    assert chunks[0].metadata["_embed_text"].startswith("[Document: Hydraulic system.]")

