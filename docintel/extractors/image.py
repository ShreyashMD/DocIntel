from __future__ import annotations
from typing import List, Tuple


class ImageExtractor:
    """Extract text from image files using OCR (pytesseract + Pillow).

    Supports: JPEG, PNG, TIFF (multi-page), BMP, WebP, GIF.
    Requires: ``pip install 'docintel[ocr]'`` (installs pytesseract + Pillow)
    and the Tesseract binary on the system PATH.
    """

    def extract(self, path: str) -> List[Tuple[int, str]]:
        """Return list of (page_number, text) tuples (1-indexed).

        Multi-page TIFFs produce one tuple per frame; all other formats
        produce a single tuple for page 1.
        """
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            raise ImportError(
                "OCR dependencies missing. Install with: "
                "pip install 'docintel[ocr]'  (pytesseract + Pillow + Tesseract binary)"
            )

        img = Image.open(path)
        pages: List[Tuple[int, str]] = []
        frame = 0

        while True:
            try:
                # Ensure RGB so Tesseract always gets a consistent mode
                rgb = img.copy().convert("RGB")
                text = pytesseract.image_to_string(rgb, config="--psm 3").strip()
                if text:
                    pages.append((frame + 1, text))
            except Exception:
                pass

            frame += 1
            try:
                img.seek(frame)
            except EOFError:
                break

        if not pages:
            pages.append((1, "[No extractable text found in image]"))

        return pages

    def extract_full(self, path: str) -> str:
        pages = self.extract(path)
        return "\n\n".join(f"[Page {n}]\n{text}" for n, text in pages)
