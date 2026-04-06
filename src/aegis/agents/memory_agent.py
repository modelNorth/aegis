"""Memory Agent - updates all memory stores after each scan."""

from __future__ import annotations

import logging
from typing import Any

from aegis.core.constants import AgentName, RiskLevel
from aegis.core.models import AgentFinding, ScanResult
from aegis.agents.base import BaseAegisAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAegisAgent):
    name = AgentName.MEMORY
    role = "Memory Consolidation Agent"
    goal = "Persist scan findings and learned patterns to memory for continuous learning"
    backstory = (
        "Memory systems specialist responsible for consolidating findings from all analysis agents "
        "into persistent episodic and semantic memory stores. Enables the system to learn from past "
        "scans and improve detection accuracy over time through accumulated experience."
    )

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        scan_result: ScanResult | None = context.get("scan_result")
        session_id = context.get("session_id")

        if not scan_result:
            return self._make_finding(0.0, [], "No scan result to memorize.")

        memories_stored = self._store_scan_memory(scan_result, session_id)
        self._store_pattern_memories(scan_result)

        return self._make_finding(
            0.0,
            [f"memories_stored:{memories_stored}"],
            f"Stored {memories_stored} memory entries from scan {scan_result.job_id}.",
            {"job_id": scan_result.job_id, "memories_stored": memories_stored},
        )

    def _store_scan_memory(self, scan_result: ScanResult, session_id: str | None) -> int:
        count = 0
        user_id = session_id or "aegis-system"

        summary_memory = (
            f"Scan {scan_result.job_id}: {scan_result.content_type} content, "
            f"risk={scan_result.risk_level}, score={scan_result.risk_score:.3f}, "
            f"injection={scan_result.is_injection}"
        )
        self.add_memory(summary_memory, user_id=user_id, metadata={"job_id": scan_result.job_id})
        count += 1

        if scan_result.is_injection:
            injection_memory = (
                f"INJECTION DETECTED in {scan_result.content_type}: "
                f"{scan_result.summary[:200]}"
            )
            self.add_memory(
                injection_memory,
                user_id="aegis-threat-db",
                metadata={"risk_level": scan_result.risk_level.value, "job_id": scan_result.job_id},
            )
            count += 1

        return count

    def _store_pattern_memories(self, scan_result: ScanResult) -> None:
        if scan_result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            for finding in scan_result.findings:
                if finding.score >= 0.6 and finding.signals:
                    pattern_memory = (
                        f"High-risk {finding.agent} signals: {', '.join(finding.signals[:5])}"
                    )
                    try:
                        self.add_memory(
                            pattern_memory,
                            user_id="aegis-pattern-db",
                            metadata={"agent": finding.agent, "score": finding.score},
                        )
                    except Exception as exc:
                        logger.debug("Failed to store pattern memory: %s", exc)

    def update_from_feedback(self, job_id: str, is_correct: bool, actual_risk_level: str | None) -> None:
        feedback_memory = (
            f"Feedback for job {job_id}: verdict was {'correct' if is_correct else 'incorrect'}. "
            f"{'Actual risk: ' + actual_risk_level if actual_risk_level and not is_correct else ''}"
        )
        self.add_memory(
            feedback_memory,
            user_id="aegis-feedback-db",
            metadata={"job_id": job_id, "is_correct": is_correct, "actual_risk": actual_risk_level},
        )
