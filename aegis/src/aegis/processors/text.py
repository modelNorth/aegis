"""Plain text processor - normalization and extraction."""

from __future__ import annotations

import re
import unicodedata

from aegis.core.constants import ZERO_WIDTH_CHARS


class TextProcessor:
    def process(self, content: str) -> ProcessedText:
        raw = content
        normalized = self._normalize(content)
        zero_width_found = self._detect_zero_width(content)
        homoglyphs_found = self._detect_homoglyphs(content)
        encoding_tricks = self._detect_encoding_tricks(content)

        return ProcessedText(
            raw=raw,
            normalized=normalized,
            zero_width_chars=zero_width_found,
            homoglyphs_detected=homoglyphs_found,
            encoding_tricks=encoding_tricks,
            char_count=len(normalized),
            line_count=normalized.count("\n") + 1,
        )

    def _normalize(self, text: str) -> str:
        for char in ZERO_WIDTH_CHARS:
            text = text.replace(char, "")
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _detect_zero_width(self, text: str) -> list[str]:
        found = []
        for char in ZERO_WIDTH_CHARS:
            if char in text:
                found.append(f"U+{ord(char):04X}")
        return found

    def _detect_homoglyphs(self, text: str) -> bool:
        homoglyph_ranges = [
            (0x0400, 0x04FF),
            (0x1D00, 0x1D7F),
            (0x2100, 0x214F),
        ]
        for char in text:
            cp = ord(char)
            if any(start <= cp <= end for start, end in homoglyph_ranges):
                return True
        return False

    def _detect_encoding_tricks(self, text: str) -> list[str]:
        tricks = []
        if "\x00" in text:
            tricks.append("null_bytes")
        rtl_chars = ["\u200f", "\u202b", "\u202e", "\u2067"]
        if any(c in text for c in rtl_chars):
            tricks.append("rtl_override")
        if re.search(r"\\u[0-9a-fA-F]{4}", text):
            tricks.append("unicode_escapes")
        if re.search(r"%[0-9a-fA-F]{2}", text):
            tricks.append("url_encoding")
        return tricks


class ProcessedText:
    def __init__(
        self,
        raw: str,
        normalized: str,
        zero_width_chars: list[str],
        homoglyphs_detected: bool,
        encoding_tricks: list[str],
        char_count: int,
        line_count: int,
    ) -> None:
        self.raw = raw
        self.normalized = normalized
        self.zero_width_chars = zero_width_chars
        self.homoglyphs_detected = homoglyphs_detected
        self.encoding_tricks = encoding_tricks
        self.char_count = char_count
        self.line_count = line_count

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "zero_width_chars": self.zero_width_chars,
            "homoglyphs_detected": self.homoglyphs_detected,
            "encoding_tricks": self.encoding_tricks,
            "char_count": self.char_count,
            "line_count": self.line_count,
        }
