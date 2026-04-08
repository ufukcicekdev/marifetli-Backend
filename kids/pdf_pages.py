"""PDF sayfalarını PNG baytlarına çevir (test AI çıkarımı)."""

from __future__ import annotations

import io


def pdf_bytes_to_png_list(data: bytes, *, max_pages: int = 10, dpi: int = 144) -> list[bytes]:
    """PyMuPDF ile rasterleştirme; en fazla `max_pages` sayfa."""
    import fitz  # PyMuPDF

    if not data or len(data) < 8:
        raise ValueError("PDF dosyası boş veya geçersiz.")
    head = data[: min(len(data), 2048)].lstrip()
    if b"%PDF" not in head[:1024]:
        raise ValueError("Geçerli bir PDF dosyası değil.")

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        total = int(doc.page_count)
        n = min(total, max(1, max_pages))
        out: list[bytes] = []
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            out.append(pix.tobytes("png"))
        return out
    finally:
        doc.close()


class PngBytesFile:
    """extract_test_from_images için file benzeri nesne (read + content_type)."""

    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)
        self.content_type = "image/png"

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            return self._buf.read()
        return self._buf.read(size)
