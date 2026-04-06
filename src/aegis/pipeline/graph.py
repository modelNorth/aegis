"""LangGraph definition for the Aegis analysis pipeline."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    StateGraph = None  # type: ignore
    START = "__start__"
    END = "__end__"

from aegis.core.models import AgentFinding, ScanResult
from aegis.pipeline.nodes import (
    behavioral_node,
    extract_node,
    guardrails_node,
    intent_node,
    memory_node,
    sanitize_node,
    semantic_node,
    structural_node,
    verdict_node,
    visual_node,
)
from aegis.pipeline.router import route_by_content_type
from aegis.pipeline.state import AegisState

logger = logging.getLogger(__name__)


class AegisGraph:
    """Compiled LangGraph for Aegis analysis."""

    def __init__(self) -> None:
        self._graph: Any | None = None
        self._compile()

    def _compile(self) -> None:
        """Compile the LangGraph."""
        if StateGraph is None:
            logger.warning("LangGraph not available, using fallback execution")
            return

        try:
            # Create the state graph
            workflow = StateGraph(AegisState)

            # Add nodes
            workflow.add_node("extract", extract_node)
            workflow.add_node("sanitize", sanitize_node)
            workflow.add_node("guardrails", guardrails_node)
            workflow.add_node("structural", structural_node)
            workflow.add_node("semantic", semantic_node)
            workflow.add_node("intent", intent_node)
            workflow.add_node("visual", visual_node)
            workflow.add_node("behavioral", behavioral_node)
            workflow.add_node("verdict", verdict_node)
            workflow.add_node("memory", memory_node)

            # Define edges
            workflow.add_edge(START, "extract")
            workflow.add_edge("extract", "sanitize")
            workflow.add_edge("sanitize", "guardrails")

            # Conditional routing after guardrails
            def route_after_guardrails(state: AegisState) -> str:
                if state.get("should_block", False):
                    return "verdict"
                return "analysis"

            workflow.add_conditional_edges(
                "guardrails",
                route_after_guardrails,
                {
                    "verdict": "verdict",
                    "analysis": "semantic",  # Start with semantic for all
                },
            )

            # Sequential analysis flow
            workflow.add_edge("semantic", "intent")
            workflow.add_edge("intent", "behavioral")

            workflow.add_edge("behavioral", "verdict")

            # Final steps
            workflow.add_edge("verdict", "memory")
            workflow.add_edge("memory", END)

            # Compile the graph
            self._graph = workflow.compile()
            logger.info("Aegis LangGraph compiled successfully")

        except Exception as exc:
            logger.error("Failed to compile LangGraph: %s", exc)
            self._graph = None

    def invoke(self, state: AegisState) -> AegisState:
        """Execute the graph with the given initial state."""
        if self._graph is not None:
            try:
                return self._graph.invoke(state)
            except Exception as exc:
                logger.error("Graph execution failed: %s", exc)
                # Fall through to fallback

        return self._fallback_execute(state)

    def _fallback_execute(self, state: AegisState) -> AegisState:
        """Fallback sequential execution when LangGraph is unavailable."""
        logger.debug("Using fallback sequential execution")

        # Run nodes sequentially
        result = extract_node(state)
        state.update(result)

        result = sanitize_node(state)
        state.update(result)

        result = guardrails_node(state)
        state.update(result)

        # Content-specific analysis
        nodes_to_run = route_by_content_type(state)
        node_map = {
            "structural": structural_node,
            "semantic": semantic_node,
            "intent": intent_node,
            "visual": visual_node,
            "behavioral": behavioral_node,
        }

        for node_name in nodes_to_run:
            if node_name in node_map:
                result = node_map[node_name](state)
                state.update(result)

        result = verdict_node(state)
        state.update(result)

        result = memory_node(state)
        state.update(result)

        return state

    def build_scan_result(self, state: AegisState) -> ScanResult:
        """Build a ScanResult from the final state."""
        from aegis.core.constants import RiskLevel

        findings: list[AgentFinding] = []
        for key in ["structural_finding", "semantic_finding", "intent_finding", "visual_finding", "behavioral_finding", "verdict_finding"]:
            finding = state.get(key)
            if finding:
                findings.append(finding)

        return ScanResult(
            job_id=state.get("job_id", "unknown"),
            risk_level=RiskLevel(state.get("risk_level", "safe")),
            risk_score=state.get("risk_score", 0.0),
            is_injection=state.get("is_injection", False),
            confidence=state.get("confidence", 0.0),
            findings=findings,
            summary=state.get("summary", ""),
            content_type=state["content_type"],
            processing_time_ms=state.get("processing_time_ms", 0),
            sanitized_content=state.get("sanitized_content"),
        )


@lru_cache(maxsize=1)
def get_graph() -> AegisGraph:
    """Get the compiled graph singleton."""
    return AegisGraph()
