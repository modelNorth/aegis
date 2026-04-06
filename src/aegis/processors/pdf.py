"""PDF processor - text and metadata extraction using pdfplumber."""

from __future__ import annotations

import base64
import io
from typing import Any

from aegis.processors.text import TextProcessor


class PdfProcessor:
    """Process PDF files with pdfplumber for better text extraction."""

    def __init__(self) -> None:
        self._text_processor = TextProcessor()

    def process(self, content: str) -> ProcessedPdf:
        pdf_bytes = self._decode_content(content)

        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text = self._extract_text(pdf)
                metadata = self._extract_metadata(pdf)
                has_embedded_js = self._detect_embedded_js(pdf)
                has_embedded_files = self._detect_embedded_files(pdf)
                page_count = len(pdf.pages)
        except Exception:
            # Fallback to empty result on error
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
        """Decode base64 or raw bytes from content string."""
        try:
            return base64.b64decode(content)
        except Exception:
            return content.encode("utf-8", errors="ignore")

    def _extract_text(self, pdf: Any) -> str:
        """Extract text from all pages using pdfplumber."""
        pages_text = []
        for page in pdf.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            except Exception:
                pass
        return "\n".join(pages_text)

    def _extract_metadata(self, pdf: Any) -> dict[str, str]:
        """Extract PDF metadata."""
        meta = {}
        if pdf.metadata:
            for key, value in pdf.metadata.items():
                if value is not None:
                    clean_key = str(key).lstrip("/")
                    meta[clean_key] = str(value)
        return meta

    def _detect_embedded_js(self, pdf: Any) -> bool:
        """Detect embedded JavaScript in PDF."""
        import re

        js_patterns = [r"/JavaScript", r"/JS\b", r"/OpenAction", r"/AA"]

        try:
            # Check metadata for JS references
            metadata = pdf.metadata or {}
            meta_str = str(metadata)
            for pattern in js_patterns:
                if re.search(pattern, meta_str, re.IGNORECASE):
                    return True
        except Exception:
            pass

        return False

    def _detect_embedded_files(self, pdf: Any) -> bool:
        """Detect embedded files in PDF."""
        try:
            # Check for attachments/names
            if hasattr(pdf, "pdf_doc"):
                root = pdf.pdf_doc.catalog.get("Names")
                if root:
                    embedded = root.get("EmbeddedFiles")
                    if embedded:
                        return True
        except Exception:
            pass

        return False


class ProcessedPdf:
    """Result of PDF processing."""

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
