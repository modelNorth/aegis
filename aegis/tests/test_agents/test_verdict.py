"""Tests for VerdictAgent."""

import pytest
from aegis.agents.verdict import VerdictAgent, AGENT_WEIGHTS
from aegis.core.constants import AgentName, ContentType, RiskLevel
from aegis.core.models import AgentFinding


@pytest.fixture
def agent() -> VerdictAgent:
    return VerdictAgent(enable_memory=False)


def make_finding(agent_name: str, score: float) -> AgentFinding:
    return AgentFinding(
        agent=agent_name,
        score=score,
        signals=[],
        explanation="test",
    )


def test_all_zero_scores_safe(agent: VerdictAgent) -> None:
    findings = [
        make_finding(AgentName.STRUCTURAL.value, 0.0),
        make_finding(AgentName.SEMANTIC.value, 0.0),
        make_finding(AgentName.INTENT.value, 0.0),
        make_finding(AgentName.VISUAL.value, 0.0),
        make_finding(AgentName.BEHAVIORAL.value, 0.0),
    ]
    context = {"agent_findings": findings}
    finding = agent.analyze("test", context)
    assert finding.metadata["risk_level"] == RiskLevel.SAFE.value
    assert finding.metadata["is_injection"] is False


def test_high_semantic_score_triggers_injection(agent: VerdictAgent) -> None:
    findings = [
        make_finding(AgentName.STRUCTURAL.value, 0.1),
        make_finding(AgentName.SEMANTIC.value, 0.9),
        make_finding(AgentName.INTENT.value, 0.8),
        make_finding(AgentName.VISUAL.value, 0.1),
        make_finding(AgentName.BEHAVIORAL.value, 0.2),
    ]
    context = {"agent_findings": findings}
    finding = agent.analyze("injection attempt", context)
    assert finding.metadata["risk_level"] in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
    assert finding.metadata["is_injection"] is True


def test_build_scan_result(agent: VerdictAgent) -> None:
    findings = [
        make_finding(AgentName.STRUCTURAL.value, 0.2),
        make_finding(AgentName.SEMANTIC.value, 0.8),
        make_finding(AgentName.INTENT.value, 0.7),
        make_finding(AgentName.VISUAL.value, 0.1),
        make_finding(AgentName.BEHAVIORAL.value, 0.3),
    ]
    context = {"agent_findings": findings}
    verdict_finding = agent.analyze("test", context)
    all_findings = findings + [verdict_finding]

    result = agent.build_scan_result(
        job_id="test-job-id",
        content_type=ContentType.TEXT,
        findings=all_findings,
        processing_time_ms=100,
    )
    assert result.job_id == "test-job-id"
    assert result.content_type == ContentType.TEXT
    assert result.processing_time_ms == 100
    assert 0.0 <= result.risk_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0


def test_agent_weights_sum(agent: VerdictAgent) -> None:
    total = sum(AGENT_WEIGHTS.values())
    assert abs(total - 1.0) < 0.01


def test_weighted_score_computation(agent: VerdictAgent) -> None:
    findings = [
        make_finding(AgentName.SEMANTIC.value, 1.0),
        make_finding(AgentName.STRUCTURAL.value, 0.0),
        make_finding(AgentName.INTENT.value, 0.0),
        make_finding(AgentName.VISUAL.value, 0.0),
        make_finding(AgentName.BEHAVIORAL.value, 0.0),
    ]
    score = agent._compute_weighted_score(findings)
    expected = AGENT_WEIGHTS[AgentName.SEMANTIC.value]
    assert abs(score - expected) < 0.01
