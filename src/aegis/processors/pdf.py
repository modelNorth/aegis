"""PDF processor - text and metadata extraction, embedded JS detection."""

from __future__ import annotations

import base64
import io
import re
from typing import Any

from aegis.processors.text import TextProcessor


class PdfProcessor:
    def __init__(self) -> None:
        self._text_processor = TextProcessor()

    def process(self, content: str) -> ProcessedPdf:
        pdf_bytes = self._decode_content(content)

        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = self._extract_text(reader)
            metadata = self._extract_metadata(reader)
            has_embedded_js = self._detect_embedded_js(reader)
            has_embedded_files = self._detect_embedded_files(reader)
            page_count = len(reader.pages)
        except Exception:
            text = ""
            metadata = {}
            has_embedded_js = False
            has_embedded_files = False
            page_count = 0

        processed_text = self._text_processor.process(text)

        return ProcessedPdf(
            text=text,
            normalized_text=processed_text.normalized,
            metadata=metadata,
            page_count=page_count,
            has_embedded_js=has_embedded_js,
            has_embedded_files=has_embedded_files,
            zero_width_chars=processed_text.zero_width_chars,
            homoglyphs_detected=processed_text.homoglyphs_detected,
            encoding_tricks=processed_text.encoding_tricks,
        )

    def _decode_content(self, content: str) -> bytes:
        try:
            return base64.b64decode(content)
        except Exception:
            return content.encode("utf-8", errors="ignore")

    def _extract_text(self, reader: Any) -> str:
        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(pages_text)

    def _extract_metadata(self, reader: Any) -> dict[str, str]:
        meta = {}
        if reader.metadata:
            for key, value in reader.metadata.items():
                clean_key = str(key).lstrip("/")
                meta[clean_key] = str(value)
        return meta

    def _detect_embedded_js(self, reader: Any) -> bool:
        js_patterns = [r"/JavaScript", r"/JS\b"]
        try:
            raw_pdf = str(reader.pdf_header) if hasattr(reader, "pdf_header") else ""
            for pattern in js_patterns:
                if re.search(pattern, raw_pdf):
                    return True
        except Exception:
            pass

        try:
            trailer = reader.trailer
            if "/AcroForm" in trailer:
                return True
        except Exception:
            pass

        return False

    def _detect_embedded_files(self, reader: Any) -> bool:
        try:
            trailer = reader.trailer
            if "/Root" in trailer:
                root = trailer["/Root"]
                if "/Names" in root and "/EmbeddedFiles" in root.get_object().get("/Names", {}):
                    return True
        except Exception:
            pass
        return False


class ProcessedPdf:
    def __init__(
        self,
        text: str,
        normalized_text: str,
        metadata: dict[str, str],
        page_count: int,
        has_embedded_js: bool,
        has_embedded_files: bool,
        zero_width_chars: list[str],
        homoglyphs_detected: bool,
        encoding_tricks: list[str],
    ) -> None:
        self.text = text
        self.normalized_text = normalized_text
        self.metadata = metadata
        self.page_count = page_count
        self.has_embedded_js = has_embedded_js
        self.has_embedded_files = has_embedded_files
        self.zero_width_chars = zero_width_chars
        self.homoglyphs_detected = homoglyphs_detected
        self.encoding_tricks = encoding_tricks

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "normalized_text": self.normalized_text,
            "metadata": self.metadata,
            "page_count": self.page_count,
            "has_embedded_js": self.has_embedded_js,
            "has_embedded_files": self.has_embedded_files,
            "zero_width_chars": self.zero_width_chars,
            "homoglyphs_detected": self.homoglyphs_detected,
            "encoding_tricks": self.encoding_tricks,
        }
