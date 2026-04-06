"""Semantic Agent - rule-based classifier with Phase 2 ML integration point."""

from __future__ import annotations

import re
from typing import Any

from aegis.core.constants import AgentName, PROMPT_INJECTION_PATTERNS
from aegis.core.models import AgentFinding
from aegis.agents.base import BaseAegisAgent


# PHASE2: Replace RuleBasedClassifier with AegisClassifier (ML model)
# Interface: classifier.predict(text: str) -> ClassifierResult
# ClassifierResult has .score (float), .label (str), .confidence (float)
class RuleBasedClassifier:
    def __init__(self) -> None:
        self._patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PROMPT_INJECTION_PATTERNS]

    def predict(self, text: str) -> "ClassifierResult":
        matches = []
        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                matches.append(match.group(0)[:100])

        if not matches:
            return ClassifierResult(score=0.0, label="safe", confidence=0.9, matched_patterns=[])

        score = min(0.9, len(matches) * 0.2 + 0.3)
        return ClassifierResult(
            score=score,
            label="injection",
            confidence=0.7 + min(0.25, len(matches) * 0.05),
            matched_patterns=matches,
        )


class ClassifierResult:
    def __init__(self, score: float, label: str, confidence: float, matched_patterns: list[str]) -> None:
        self.score = score
        self.label = label
        self.confidence = confidence
        self.matched_patterns = matched_patterns


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
        # PHASE2: Replace with AegisClassifier(model_path=config.classifier_model_path)
        self._classifier = RuleBasedClassifier()

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        text = self._extract_text(content, context)

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
            {"classifier_label": result.label, "confidence": result.confidence},
        )

    def _extract_text(self, content: str, context: dict[str, Any]) -> str:
        processed = context.get("processed", {})
        if "all_text" in processed:
            return processed["all_text"]
        if "normalized_text" in processed:
            return processed["normalized_text"]
        if "ocr_text" in processed:
            return processed.get("ocr_text", "") + " " + content
        if "normalized" in processed:
            return processed["normalized"]
        return content

    def _check_additional_patterns(self, text: str) -> tuple[list[str], float]:
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
