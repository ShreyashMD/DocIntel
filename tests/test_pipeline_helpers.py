from pathlib import Path

from docintel._pipeline import Pipeline, _sha256


def test_supported_extensions_are_current_extractors() -> None:
    assert Pipeline.supported_extensions() == (".log", ".md", ".pdf", ".rst", ".txt")


def test_iter_supported_files_respects_recursive_flag(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "ignored.csv").write_text("alpha", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.md").write_text("beta", encoding="utf-8")

    shallow = list(Pipeline._iter_supported_files(tmp_path, recursive=False))
    recursive = list(Pipeline._iter_supported_files(tmp_path, recursive=True))

    assert [path.name for path in shallow] == ["a.txt"]
    assert [path.name for path in recursive] == ["a.txt", "b.md"]


def test_sha256_is_stable(tmp_path) -> None:
    path = Path(tmp_path / "doc.txt")
    path.write_text("industrial docs", encoding="utf-8")

    assert _sha256(path) == _sha256(path)

