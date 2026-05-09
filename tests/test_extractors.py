from docintel.extractors.text import TextExtractor


def test_text_extractor_splits_blank_line_paragraphs(tmp_path) -> None:
    path = tmp_path / "inspection.log"
    path.write_text("First finding.\n\nSecond finding.", encoding="utf-8")

    pages = TextExtractor().extract(str(path))

    assert pages == [(1, "First finding."), (2, "Second finding.")]

