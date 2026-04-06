"""Verdict Agent - score aggregation and final risk decision."""

from __future__ import annotations

from typing import Any

from aegis.core.constants import AgentName, RISK_SCORE_THRESHOLDS, RiskLevel
from aegis.core.models import AgentFinding, ScanResult
from aegis.agents.base import BaseAegisAgent


AGENT_WEIGHTS: dict[str, float] = {
    AgentName.STRUCTURAL.value: 0.20,
    AgentName.SEMANTIC.value: 0.35,
    AgentName.INTENT.value: 0.25,
    AgentName.VISUAL.value: 0.10,
    AgentName.BEHAVIORAL.value: 0.10,
}


class VerdictAgent(BaseAegisAgent):
    name = AgentName.VERDICT
    role = "Security Verdict Aggregator"
    goal = "Synthesize findings from all agents to produce a final authoritative risk verdict"
    backstory = (
        "Senior security decision system with expertise in combining evidence from multiple specialized "
        "analysis agents. Applies weighted scoring, contextual adjustment, and confidence calibration "
        "to produce final verdicts that minimize both false positives and false negatives."
    )

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        findings: list[AgentFinding] = context.get("agent_findings", [])
        score = self._compute_weighted_score(findings)
        score = self._apply_contextual_boosts(score, findings, context)
        risk_level = self._score_to_risk_level(score)
        is_injection = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        confidence = self._compute_confidence(findings, score)

        summary = self._build_summary(risk_level, score, findings, is_injection)

        self.add_memory(
            f"Verdict: {risk_level} (score={score:.3f}, injection={is_injection})",
            metadata={"score": score, "risk_level": risk_level.value},
        )

        return self._make_finding(
            score,
            [f"verdict:{risk_level.value}", f"injection:{is_injection}"],
            summary,
            {
                "risk_level": risk_level.value,
                "is_injection": is_injection,
                "confidence": confidence,
                "summary": summary,
            },
        )

    def _compute_weighted_score(self, findings: list[AgentFinding]) -> float:
        if not findings:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for finding in findings:
            weight = AGENT_WEIGHTS.get(finding.agent, 0.1)
            weighted_sum += finding.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _apply_contextual_boosts(
        self,
        score: float,
        findings: list[AgentFinding],
        context: dict[str, Any],
    ) -> float:
        high_score_agents = sum(1 for f in findings if f.score >= 0.7)
        if high_score_agents >= 3:
            score = min(1.0, score * 1.2)

        critical_signals = ["pdf_embedded_javascript", "ocr_injection_pattern", "lsb_steganography_suspected"]
        all_signals = [sig for f in findings for sig in f.signals]
        if any(sig.startswith(cs) for sig in all_signals for cs in critical_signals):
            score = min(1.0, score + 0.1)

        return score

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= RISK_SCORE_THRESHOLDS[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        if score >= RISK_SCORE_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        if score >= RISK_SCORE_THRESHOLDS[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        if score >= RISK_SCORE_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        return RiskLevel.SAFE

    def _compute_confidence(self, findings: list[AgentFinding], score: float) -> float:
        if not findings:
            return 0.5

        score_variance = sum((f.score - score) ** 2 for f in findings) / len(findings)
        agreement_factor = max(0.0, 1.0 - score_variance)

        active_agents = len([f for f in findings if f.score > 0.1])
        coverage_factor = min(1.0, active_agents / max(len(AGENT_WEIGHTS), 1))

        return round(0.6 * agreement_factor + 0.4 * coverage_factor, 4)

    def _build_summary(
        self,
        risk_level: RiskLevel,
        score: float,
        findings: list[AgentFinding],
        is_injection: bool,
    ) -> str:
        if not is_injection:
            return (
                f"Content assessed as {risk_level.upper()} risk (score={score:.3f}). "
                f"No prompt injection attack detected across {len(findings)} analysis agents."
            )

        triggering_agents = [f.agent for f in findings if f.score >= 0.5]
        return (
            f"PROMPT INJECTION DETECTED - Risk level: {risk_level.upper()} (score={score:.3f}). "
            f"Triggered by agents: {', '.join(triggering_agents)}. "
            f"Immediate review recommended."
        )

    def build_scan_result(
        self,
        job_id: str,
        content_type: Any,
        findings: list[AgentFinding],
        processing_time_ms: int,
    ) -> ScanResult:
        verdict_finding = next((f for f in findings if f.agent == self.name.value), None)

        if verdict_finding:
            meta = verdict_finding.metadata
            risk_level = RiskLevel(meta.get("risk_level", RiskLevel.SAFE.value))
            is_injection = bool(meta.get("is_injection", False))
            confidence = float(meta.get("confidence", 0.5))
            summary = str(meta.get("summary", ""))
            score = verdict_finding.score
        else:
            risk_level = RiskLevel.SAFE
            is_injection = False
            confidence = 0.5
            summary = "Analysis incomplete."
            score = 0.0

        return ScanResult(
            job_id=job_id,
            risk_level=risk_level,
            risk_score=score,
            is_injection=is_injection,
            confidence=confidence,
            findings=findings,
            summary=summary,
            content_type=content_type,
            processing_time_ms=processing_time_ms,
        )
