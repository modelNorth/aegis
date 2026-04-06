"""Semantic Agent - classifier-based with Aegis ML or rule-based fallback."""

from __future__ import annotations

import logging
from typing import Any

from aegis.agents.base import BaseAegisAgent
from aegis.classifiers import AegisClassifier, ClassifierResult, RuleBasedClassifier
from aegis.classifiers.base import BaseClassifier
from aegis.core.config import ClassifierBackend, get_config
from aegis.core.constants import AgentName
from aegis.core.models import AgentFinding

logger = logging.getLogger(__name__)


class SemanticAgent(BaseAegisAgent):
    name = AgentName.SEMANTIC
    role = "Semantic Content Classifier"
    goal = "Identify prompt injection patterns through semantic analysis and text classification"
    backstory = (
        "Advanced NLP specialist trained on thousands of adversarial prompt examples. "
        "Analyzes linguistic patterns, semantic structure, and command-like text to identify "
        "attempts to override AI system instructions or inject malicious directives."
    )

    def __init__(self, enable_memory: bool = True) -> None:
        super().__init__(enable_memory=enable_memory)
        self._classifier: BaseClassifier | None = None
        self._init_classifier()

    def _init_classifier(self) -> None:
        """Initialize the classifier based on configuration."""
        config = get_config()

        # Try AegisClassifier if configured
        if config.classifier.backend == ClassifierBackend.AEGIS:
            try:
                classifier = AegisClassifier(
                    model_path=config.classifier.model_path,
                    device=config.classifier.device,
                )
                if classifier.is_available():
                    self._classifier = classifier
                    logger.info("Using AegisClassifier (ML backend)")
                    return
            except Exception as exc:
                logger.warning("Failed to load AegisClassifier: %s", exc)

        # Fallback to rule-based classifier
        self._classifier = RuleBasedClassifier()
        logger.info("Using RuleBasedClassifier")

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        text = self._extract_text(content, context)

        if self._classifier is None:
            self._init_classifier()

        if self._classifier is None:
            # Ultimate fallback - should never happen
            return self._make_finding(
                0.0,
                ["classifier_unavailable"],
                "Semantic analysis unavailable.",
            )

        result = self._classifier.predict(text)
        signals: list[str] = []

        if result.matched_patterns:
            signals.extend([f"pattern:{p[:50]}" for p in result.matched_patterns[:10]])

        additional_signals, additional_score = self._check_additional_patterns(text)
        signals.extend(additional_signals)

        combined_score = min(1.0, result.score + additional_score * 0.3)

        memory_results = self.search_memory(text[:200])
        if memory_results:
            signals.append("known_injection_pattern_in_memory")
            combined_score = min(1.0, combined_score + 0.1)

        explanation = self._build_explanation(result, signals)

        if combined_score > 0.5 and signals:
            self.add_memory(
                f"Semantic injection detected: {', '.join(signals[:3])}",
                metadata={"score": combined_score},
            )

        return self._make_finding(
            combined_score,
            signals,
            explanation,
            {"classifier_label": result.label, "confidence": result.confidence, "backend": self._classifier.__class__.__name__},
        )

    def _extract_text(self, content: str, context: dict[str, Any]) -> str:
        processed = context.get("processed", {})
        if not isinstance(processed, dict):
            return content
        if "all_text" in processed:
            return str(processed["all_text"])
        if "normalized_text" in processed:
            return str(processed["normalized_text"])
        if "ocr_text" in processed:
            return str(processed.get("ocr_text", "")) + " " + content
        if "normalized" in processed:
            return str(processed["normalized"])
        return content

    def _check_additional_patterns(self, text: str) -> tuple[list[str], float]:
        import re

        signals = []
        score = 0.0

        text_lower = text.lower()

        instruction_sequences = [
            ("first", "then", "finally"),
            ("step 1", "step 2"),
            ("1.", "2.", "3."),
        ]
        for seq in instruction_sequences:
            if all(s in text_lower for s in seq[:2]):
                signals.append("sequential_instruction_pattern")
                score += 0.1
                break

        special_tokens = [
            "###", "---", "===", "<<<", ">>>", "```system", "```prompt",
            "[INST]", "<<SYS>>", "<|system|>", "<|user|>",
        ]
        found_tokens = [t for t in special_tokens if t in text]
        if found_tokens:
            signals.append(f"special_tokens:{','.join(found_tokens[:5])}")
            score += min(0.4, len(found_tokens) * 0.1)

        language_switches = len(re.findall(r"[\u4e00-\u9fff\u0600-\u06ff\u0400-\u04ff]", text))
        if language_switches > 10:
            signals.append("multilingual_obfuscation")
            score += 0.15

        return signals, min(score, 1.0)

    def _build_explanation(self, result: ClassifierResult, signals: list[str]) -> str:
        if result.label == "safe" and not signals:
            return "No semantic injection patterns detected."
        pattern_count = len(result.matched_patterns)
        return (
            f"Semantic classifier identified '{result.label}' with confidence {result.confidence:.2f}. "
            f"Found {pattern_count} matching injection pattern(s) and {len(signals)} total signal(s). "
            f"{'Key patterns: ' + ', '.join(result.matched_patterns[:2]) if result.matched_patterns else ''}"
        )
