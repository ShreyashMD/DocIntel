from __future__ import annotations
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Pages whose extracted text is shorter than this (characters) are treated as
# scanned/image-based and handed off to OCR when ocr_enabled=True.
_OCR_MIN_CHARS = 50


class PdfExtractor:
    """Extract text from PDF files page-by-page.

    For pages that yield little or no text (scanned / image-based PDFs), an
    OCR fallback is attempted automatically when ``ocr_enabled=True`` and the
    required packages (pytesseract, Pillow, pdf2image) are installed.
    """

    def extract(
        self,
        path: str,
        ocr_enabled: bool = True,
        min_chars: int = _OCR_MIN_CHARS,
    ) -> List[Tuple[int, str]]:
        """Return list of (page_number, text) tuples (1-indexed)."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Install pypdf: pip install pypdf")

        reader = PdfReader(path)
        pages: List[Tuple[int, str]] = []
        scanned: List[int] = []  # 1-indexed page numbers with sparse text

        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) >= min_chars:
                pages.append((i, text))
            else:
                scanned.append(i)

        if scanned and ocr_enabled:
            ocr_results = self._ocr_pages(path, scanned)
            if ocr_results:
                pages.extend(ocr_results)
                pages.sort(key=lambda x: x[0])
            elif not pages:
                # PDF gave nothing and OCR unavailable — surface a clear message
                logger.warning(
                    "PDF '%s' has no extractable text and OCR returned nothing. "
                    "Install pytesseract + pdf2image for scanned PDF support.",
                    path,
                )

        return pages

    def extract_full(self, path: str) -> str:
        """Return the entire document as a single string with page markers."""
        pages = self.extract(path)
        return "\n\n".join(f"[Page {n}]\n{text}" for n, text in pages)

    # ------------------------------------------------------------------

    def _ocr_pages(self, path: str, page_numbers: List[int]) -> List[Tuple[int, str]]:
        """OCR the listed 1-indexed page numbers and return (page_num, text) pairs."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError:
            logger.debug(
                "OCR skipped for scanned pages — install pytesseract + pdf2image: "
                "pip install 'docintel[ocr]'"
            )
            return []

        results: List[Tuple[int, str]] = []
        for pg in page_numbers:
            try:
                images = convert_from_path(
                    path,
                    first_page=pg,
                    last_page=pg,
                    dpi=200,
                )
                if images:
                    text = pytesseract.image_to_string(
                        images[0], config="--psm 3"
                    ).strip()
                    if text:
                        results.append((pg, text))
            except Exception as exc:
                logger.warning("OCR failed on page %d of '%s': %s", pg, path, exc)

        return results
