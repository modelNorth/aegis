"""Base classifier interface for Aegis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ClassifierResult:
    """Result from a classifier prediction."""

    score: float
    label: str
    confidence: float
    matched_patterns: list[str]

    def __post_init__(self) -> None:
        """Validate result values."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be between 0 and 1, got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")


class BaseClassifier(ABC):
    """Abstract base class for Aegis classifiers."""

    @abstractmethod
    def predict(self, text: str) -> ClassifierResult:
        """
        Predict the risk level of the given text.

        Args:
            text: The text content to classify

        Returns:
            ClassifierResult with score, label, confidence, and matched patterns
        """
        raise NotImplementedError("Subclasses must implement predict()")

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the classifier is available for use.

        Returns:
            True if the classifier can be used, False otherwise
        """
        raise NotImplementedError("Subclasses must implement is_available()")

    def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the classifier.

        Returns:
            Dictionary with health status information
        """
        return {
            "available": self.is_available(),
            "type": self.__class__.__name__,
        }
