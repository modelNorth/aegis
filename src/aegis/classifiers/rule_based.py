"""Rule-based classifier for prompt injection detection."""

from __future__ import annotations

import re

from aegis.classifiers.base import BaseClassifier, ClassifierResult
from aegis.core.constants import PROMPT_INJECTION_PATTERNS


class RuleBasedClassifier(BaseClassifier):
    """Rule-based classifier using regex patterns."""

    def __init__(self) -> None:
        self._patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PROMPT_INJECTION_PATTERNS]

    def is_available(self) -> bool:
        """Rule-based classifier is always available."""
        return True

    def predict(self, text: str) -> ClassifierResult:
        """Predict using rule-based pattern matching."""
        matches = []
        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                matches.append(match.group(0)[:100])

        if not matches:
            return ClassifierResult(score=0.0, label="safe", confidence=0.9, matched_patterns=[])

        # Calculate score based on number of matches
        score = min(0.9, len(matches) * 0.2 + 0.3)

        return ClassifierResult(
            score=score,
            label="injection",
            confidence=0.7 + min(0.25, len(matches) * 0.05),
            matched_patterns=matches,
        )
