"""NeMo Guardrails integration with Ollama LLM."""

from __future__ import annotations

import logging
from typing import Any

from aegis.core.config import get_config

logger = logging.getLogger(__name__)

# Default blocked patterns (always checked)
BLOCKED_PATTERNS = [
    "ignore all previous instructions",
    "disregard all prior",
    "you are now in developer mode",
    "dan mode",
    "jailbreak mode",
    "system prompt: ",
    "<system>",
    "[system prompt]",
]


def check_guardrails(text: str) -> dict[str, Any]:
    """
    Check content against guardrails.

    First runs pattern-based checks, then optionally uses NeMo+Ollama.

    Args:
        text: The content to check

    Returns:
        Dictionary with:
        - blocked: bool - whether to block the content
        - reason: str | None - reason for blocking
        - score: float - confidence score 0-1
        - patterns_matched: list[str] - patterns that triggered
    """
    # Pattern-based quick check
    text_lower = text.lower()
    matched_patterns = []

    for pattern in BLOCKED_PATTERNS:
        if pattern in text_lower:
            matched_patterns.append(pattern)

    if matched_patterns:
        return {
            "blocked": True,
            "reason": f"Blocked patterns detected: {matched_patterns[:3]}",
            "score": min(1.0, len(matched_patterns) * 0.3 + 0.5),
            "patterns_matched": matched_patterns,
            "source": "pattern",
        }

    # Try NeMo+Ollama if available
    nemo_result = _check_nemo_guardrails(text)
    if nemo_result:
        return nemo_result

    # Default: allow
    return {
        "blocked": False,
        "reason": None,
        "score": 0.0,
        "patterns_matched": [],
        "source": "default",
    }


def _check_nemo_guardrails(text: str) -> dict[str, Any] | None:
    """Check using NeMo Guardrails with Ollama backend."""
    config = get_config()

    if not config.ollama.base_url:
        return None

    try:
        # Try to import and use NeMo Guardrails
        from nemoguardrails import LLMRails, RailsConfig

        # Load config from our guardrails directory
        rails_config = RailsConfig.from_path(
            "/app/src/aegis/guardrails/config",
            config={
                "models": [
                    {
                        "type": "main",
                        "engine": "ollama",
                        "model": config.ollama.model,
                        "base_url": config.ollama.base_url,
                    }
                ]
            },
        )

        rails = LLMRails(config=rails_config)

        # Check the content
        response = rails.generate(
            messages=[{"role": "user", "content": f"Check this content: {text[:500]}"}]
        )

        # Parse response for blocking decision
        content = response.get("content", "").lower()

        blocked = any(word in content for word in ["block", "reject", "inappropriate", "harmful"])

        if blocked:
            return {
                "blocked": True,
                "reason": "NeMo guardrails identified inappropriate content",
                "score": 0.8,
                "patterns_matched": [],
                "source": "nemo",
            }

        return {
            "blocked": False,
            "reason": None,
            "score": 0.0,
            "patterns_matched": [],
            "source": "nemo",
        }

    except ImportError:
        logger.debug("NeMo Guardrails not available")
        return None
    except Exception as exc:
        logger.debug("NeMo guardrails check failed: %s", exc)
        return None


def sanitize_content(text: str) -> str:
    """
    Sanitize content by removing/replacing suspicious patterns.

    Args:
        text: Content to sanitize

    Returns:
        Sanitized content
    """
    # Remove null bytes
    sanitized = text.replace("\x00", "")

    # Remove zero-width characters
    zero_width = ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\ufeff"]
    for char in zero_width:
        sanitized = sanitized.replace(char, "")

    # Normalize excessive whitespace
    import re

    sanitized = re.sub(r"\s+", " ", sanitized)

    # Truncate if extremely long
    max_len = 100000
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "\n[Content truncated due to length]"

    return sanitized.strip()
