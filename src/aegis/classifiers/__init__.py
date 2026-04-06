"""Aegis classifier module with ML and rule-based options."""

from aegis.classifiers.aegis import AegisClassifier
from aegis.classifiers.base import BaseClassifier, ClassifierResult
from aegis.classifiers.rule_based import RuleBasedClassifier

__all__ = [
    "BaseClassifier",
    "ClassifierResult",
    "AegisClassifier",
    "RuleBasedClassifier",
]
