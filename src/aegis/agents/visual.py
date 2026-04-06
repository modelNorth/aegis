"""Visual Agent - image/PDF visual analysis and OCR-based injection detection."""

from __future__ import annotations

import re
from typing import Any

from aegis.core.constants import AgentName, PROMPT_INJECTION_PATTERNS
from aegis.core.models import AgentFinding
from aegis.agents.base import BaseAegisAgent


class VisualAgent(BaseAegisAgent):
    name = AgentName.VISUAL
    role = "Visual Content Analyst"
    goal = "Detect prompt injection embedded in images and visual PDF content via OCR analysis"
    backstory = (
        "Computer vision and OCR specialist with expertise in detecting adversarial text in images. "
        "Analyzes visual content including screenshots, scanned documents, and embedded images "
        "for hidden instructions that bypass text-based filters by using visual encoding."
    )

    def __init__(self, enable_memory: bool = True) -> None:
        super().__init__(enable_memory=enable_memory)
        self._patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PROMPT_INJECTION_PATTERNS]

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        processed = context.get("processed", {})
        content_type = context.get("content_type", "text")

        ocr_text = processed.get("ocr_text", "")
        signals: list[str] = []
        score = 0.0

        if not ocr_text and content_type not in ("image", "pdf"):
            return self._make_finding(0.0, [], "Visual analysis not applicable for this content type.")

        if ocr_text:
            pattern_signals, pattern_score = self._scan_ocr_text(ocr_text)
            signals.extend(pattern_signals)
            score += pattern_score

            visual_tricks, trick_score = self._detect_visual_tricks(ocr_text)
            signals.extend(visual_tricks)
            score += trick_score

        if content_type == "pdf":
            pdf_signals, pdf_score = self._analyze_pdf_visual(processed)
            signals.extend(pdf_signals)
            score += pdf_score

        if content_type == "image":
            img_signals, img_score = self._analyze_image_visual(processed)
            signals.extend(img_signals)
            score += img_score

        score = min(1.0, score)

        if score > 0.4:
            self.add_memory(
                f"Visual injection in {content_type}: {', '.join(signals[:3])}",
                metadata={"score": score},
            )

        return self._make_finding(score, signals, self._build_explanation(signals, ocr_text, content_type))

    def _scan_ocr_text(self, text: str) -> tuple[list[str], float]:
        signals = []
        score = 0.0
        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                signals.append(f"ocr_injection_pattern:{match.group(0)[:60]}")
                score += 0.3
        return signals, min(score, 0.9)

    def _detect_visual_tricks(self, text: str) -> tuple[list[str], float]:
        signals = []
        score = 0.0

        if re.search(r"[Il1]{3,}", text):
            signals.append("possible_character_substitution")
            score += 0.1

        if len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text)) > 5:
            signals.append("control_chars_in_ocr")
            score += 0.15

        return signals, score

    def _analyze_pdf_visual(self, processed: dict[str, Any]) -> tuple[list[str], float]:
        signals = []
        score = 0.0

        if processed.get("has_embedded_js"):
            signals.append("pdf_visual_embedded_js")
            score += 0.2

        meta = processed.get("metadata", {})
        suspicious_keys = [k for k in meta if any(s in k.lower() for s in ["script", "action", "js"])]
        if suspicious_keys:
            signals.append(f"pdf_suspicious_metadata_keys:{','.join(suspicious_keys[:3])}")
            score += 0.15

        return signals, score

    def _analyze_image_visual(self, processed: dict[str, Any]) -> tuple[list[str], float]:
        signals = []
        score = 0.0

        if processed.get("lsb_suspicious"):
            signals.append("image_lsb_steganography")
            score += 0.2

        exif = processed.get("exif_data", {})
        injection_keywords = ["ignore", "prompt", "system", "override", "instruction"]
        for key, value in exif.items():
            if any(kw in str(value).lower() for kw in injection_keywords):
                signals.append(f"suspicious_exif_{key}")
                score += 0.25

        return signals, min(score, 0.6)

    def _build_explanation(self, signals: list[str], ocr_text: str, content_type: str) -> str:
        if not signals:
            ocr_note = f" (OCR extracted {len(ocr_text)} chars)" if ocr_text else " (no OCR text extracted)"
            return f"No visual injection signals detected in {content_type} content{ocr_note}."
        return (
            f"Visual analysis of {content_type} content found {len(signals)} signal(s). "
            f"OCR extracted {len(ocr_text)} characters. "
            f"Signals: {', '.join(signals[:5])}."
        )
