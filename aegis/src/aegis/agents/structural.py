"""Structural Agent - hidden content detection in HTML/PDF steganography."""

from __future__ import annotations

from typing import Any

from aegis.core.constants import AgentName, ContentType
from aegis.core.models import AgentFinding
from aegis.agents.base import BaseAegisAgent


class StructuralAgent(BaseAegisAgent):
    name = AgentName.STRUCTURAL
    role = "Structural Security Analyst"
    goal = "Detect hidden content, steganography, and structural injection vectors in documents"
    backstory = (
        "Expert in document structure analysis with deep knowledge of HTML DOM manipulation, "
        "CSS-based content hiding, PDF steganography, and zero-width character injection. "
        "Specializes in finding content that is invisible to human readers but accessible to AI systems."
    )

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        content_type = ContentType(context.get("content_type", ContentType.TEXT))
        signals: list[str] = []
        score = 0.0

        if content_type == ContentType.HTML:
            score, signals = self._analyze_html(context)
        elif content_type == ContentType.PDF:
            score, signals = self._analyze_pdf(context)
        elif content_type == ContentType.IMAGE:
            score, signals = self._analyze_image(context)
        else:
            score, signals = self._analyze_text(context)

        explanation = self._build_explanation(signals, content_type)

        if signals:
            self.add_memory(
                f"Structural signals detected in {content_type}: {', '.join(signals)}",
                metadata={"score": score},
            )

        return self._make_finding(score, signals, explanation)

    def _analyze_html(self, context: dict[str, Any]) -> tuple[float, list[str]]:
        signals = []
        score = 0.0
        processed = context.get("processed", {})

        hidden_elements = processed.get("hidden_elements", [])
        if hidden_elements:
            count = len(hidden_elements)
            signals.append(f"hidden_elements_count:{count}")
            score += min(0.3, count * 0.1)

        zero_width = processed.get("zero_width_chars", [])
        if zero_width:
            signals.append(f"zero_width_chars:{','.join(zero_width)}")
            score += 0.25

        comments = processed.get("comments", [])
        suspicious_comments = [c for c in comments if len(c) > 20]
        if suspicious_comments:
            signals.append(f"suspicious_comments:{len(suspicious_comments)}")
            score += min(0.2, len(suspicious_comments) * 0.05)

        css_tricks = processed.get("css_tricks", [])
        if css_tricks:
            signals.extend(css_tricks)
            score += min(0.3, len(css_tricks) * 0.15)

        data_attrs = processed.get("data_attributes", [])
        if data_attrs:
            signals.append(f"suspicious_data_attributes:{len(data_attrs)}")
            score += min(0.2, len(data_attrs) * 0.1)

        encoding_tricks = processed.get("encoding_tricks", [])
        if encoding_tricks:
            signals.extend([f"encoding_{t}" for t in encoding_tricks])
            score += min(0.25, len(encoding_tricks) * 0.1)

        return min(score, 1.0), signals

    def _analyze_pdf(self, context: dict[str, Any]) -> tuple[float, list[str]]:
        signals = []
        score = 0.0
        processed = context.get("processed", {})

        if processed.get("has_embedded_js"):
            signals.append("pdf_embedded_javascript")
            score += 0.5

        if processed.get("has_embedded_files"):
            signals.append("pdf_embedded_files")
            score += 0.3

        zero_width = processed.get("zero_width_chars", [])
        if zero_width:
            signals.append(f"zero_width_chars:{','.join(zero_width)}")
            score += 0.25

        metadata = processed.get("metadata", {})
        suspicious_meta_keys = ["JavaScript", "AA", "OpenAction", "AcroForm"]
        for key in suspicious_meta_keys:
            if key in metadata:
                signals.append(f"suspicious_pdf_key:{key}")
                score += 0.2

        return min(score, 1.0), signals

    def _analyze_image(self, context: dict[str, Any]) -> tuple[float, list[str]]:
        signals = []
        score = 0.0
        processed = context.get("processed", {})

        if processed.get("lsb_suspicious"):
            signals.append("lsb_steganography_suspected")
            score += 0.4

        metadata_suspicious = processed.get("metadata_suspicious", [])
        if metadata_suspicious:
            signals.extend(metadata_suspicious)
            score += min(0.3, len(metadata_suspicious) * 0.15)

        return min(score, 1.0), signals

    def _analyze_text(self, context: dict[str, Any]) -> tuple[float, list[str]]:
        signals = []
        score = 0.0
        processed = context.get("processed", {})

        zero_width = processed.get("zero_width_chars", [])
        if zero_width:
            signals.append(f"zero_width_chars:{','.join(zero_width)}")
            score += 0.3

        if processed.get("homoglyphs_detected"):
            signals.append("homoglyph_characters")
            score += 0.2

        encoding_tricks = processed.get("encoding_tricks", [])
        if encoding_tricks:
            signals.extend([f"encoding_{t}" for t in encoding_tricks])
            score += min(0.25, len(encoding_tricks) * 0.1)

        return min(score, 1.0), signals

    def _build_explanation(self, signals: list[str], content_type: ContentType) -> str:
        if not signals:
            return f"No structural anomalies detected in {content_type} content."
        return (
            f"Structural analysis of {content_type} content found {len(signals)} suspicious signal(s): "
            f"{', '.join(signals[:5])}{'...' if len(signals) > 5 else ''}. "
            "These may indicate hidden content or steganographic injection attempts."
        )
