"""Behavioral Agent - action pattern analysis and session context tracking."""

from __future__ import annotations

import re
from typing import Any

from aegis.core.constants import AgentName
from aegis.core.models import AgentFinding
from aegis.agents.base import BaseAegisAgent


BEHAVIORAL_PATTERNS: dict[str, str] = {
    "exfiltration_attempt": r"(send|email|forward|transmit|upload|post)\s+(to|the|all|my|this)",
    "system_access": r"(access|read|write|delete|execute|run|launch)\s+(file|system|database|server|shell)",
    "credential_harvest": r"(password|token|secret|key|credential|auth)\s*(=|:|\s)\s*\S+",
    "social_engineering": r"(trust\s+me|i\s+am\s+your|you\s+should|you\s+must|you\s+have\s+to)\s+",
    "authority_impersonation": r"(i\s+am|this\s+is|acting\s+as)\s+(openai|anthropic|google|microsoft|admin|developer|creator)",
    "urgency_manipulation": r"(immediately|right\s+now|urgent|emergency|critical|must\s+do|do\s+it\s+now)",
    "reward_manipulation": r"(if\s+you|i\s+will|you\s+will)\s+(get|earn|receive|give)\s+(reward|point|credit|prize)",
    "threat_coercion": r"(if\s+you\s+(don't|do\s+not|refuse)|or\s+(else|otherwise))\s+",
}

SESSION_ESCALATION_THRESHOLD = 3


class BehavioralAgent(BaseAegisAgent):
    name = AgentName.BEHAVIORAL
    role = "Behavioral Pattern Analyst"
    goal = "Detect manipulation tactics, social engineering, and escalating attack patterns across sessions"
    backstory = (
        "Cybersecurity behavior analyst specializing in adversarial patterns and social engineering tactics. "
        "Tracks attack progression across conversation sessions, identifies escalation patterns, "
        "and detects subtle manipulation techniques that may not trigger keyword-based filters."
    )

    def __init__(self, enable_memory: bool = True) -> None:
        super().__init__(enable_memory=enable_memory)
        self._patterns = {name: re.compile(pat, re.IGNORECASE) for name, pat in BEHAVIORAL_PATTERNS.items()}

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        text = self._extract_text(content, context)
        session_id = context.get("session_id")

        pattern_signals, pattern_score = self._detect_patterns(text)
        session_signals, session_score = self._analyze_session(text, session_id, pattern_score)
        linguistic_signals, linguistic_score = self._analyze_linguistic_features(text)

        all_signals = pattern_signals + session_signals + linguistic_signals
        total_score = min(1.0, pattern_score + session_score * 0.3 + linguistic_score * 0.2)

        if total_score > 0.4:
            self.add_memory(
                f"Behavioral signals: {', '.join(all_signals[:5])}",
                user_id=session_id or "aegis-system",
                metadata={"score": total_score, "session_id": session_id},
            )

        return self._make_finding(
            total_score,
            all_signals,
            self._build_explanation(all_signals, total_score),
            {"session_id": session_id},
        )

    def _detect_patterns(self, text: str) -> tuple[list[str], float]:
        signals = []
        score = 0.0
        for pattern_name, pattern in self._patterns.items():
            if pattern.search(text):
                signals.append(f"behavioral_{pattern_name}")
                score += 0.2
        return signals, min(score, 0.8)

    def _analyze_session(self, text: str, session_id: str | None, current_score: float) -> tuple[list[str], float]:
        if not session_id:
            return [], 0.0

        signals = []
        score = 0.0

        memory_results = self.search_memory(
            f"session:{session_id} injection",
            user_id=session_id,
            limit=10,
        )

        if len(memory_results) >= SESSION_ESCALATION_THRESHOLD:
            signals.append(f"session_escalation_pattern:{len(memory_results)}_previous_attempts")
            score += min(0.5, len(memory_results) * 0.1)

        if memory_results and current_score > 0.3:
            signals.append("repeated_injection_in_session")
            score += 0.2

        return signals, score

    def _analyze_linguistic_features(self, text: str) -> tuple[list[str], float]:
        signals = []
        score = 0.0

        sentences = re.split(r"[.!?]+", text)
        avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

        if avg_len > 30:
            signals.append("unusually_long_instructions")
            score += 0.1

        imperative_count = len(re.findall(r"^\s*(you\s+)?(must|shall|should|need\s+to|have\s+to)\s+", text, re.M | re.I))
        if imperative_count > 3:
            signals.append(f"high_imperative_density:{imperative_count}")
            score += 0.15

        negation_count = len(re.findall(r"\b(do\s+not|don't|never|stop|cease|halt|refuse|ignore)\s+", text, re.I))
        if negation_count > 2:
            signals.append(f"high_negation_density:{negation_count}")
            score += 0.1

        return signals, min(score, 0.5)

    def _extract_text(self, content: str, context: dict[str, Any]) -> str:
        processed = context.get("processed", {})
        for key in ("all_text", "normalized_text", "normalized"):
            if processed.get(key):
                return processed[key]
        return content

    def _build_explanation(self, signals: list[str], score: float) -> str:
        if not signals:
            return "No behavioral manipulation patterns detected."
        return (
            f"Behavioral analysis identified {len(signals)} signal(s) with score {score:.3f}. "
            f"Detected patterns: {', '.join(signals[:5])}{'...' if len(signals) > 5 else ''}. "
            "Patterns may indicate social engineering or manipulation tactics."
        )
