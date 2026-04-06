"""Crew orchestrator - coordinates all agents for content scanning."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aegis.core.constants import ContentType
from aegis.core.models import AgentFinding, ScanRequest, ScanResult
from aegis.agents.behavioral import BehavioralAgent
from aegis.agents.intent import IntentAgent
from aegis.agents.memory_agent import MemoryAgent
from aegis.agents.semantic import SemanticAgent
from aegis.agents.structural import StructuralAgent
from aegis.agents.verdict import VerdictAgent
from aegis.agents.visual import VisualAgent
from aegis.processors.html import HtmlProcessor
from aegis.processors.image import ImageProcessor
from aegis.processors.pdf import PdfProcessor
from aegis.processors.text import TextProcessor

logger = logging.getLogger(__name__)


class AegisCrew:
    def __init__(self, enable_memory: bool = True) -> None:
        self._structural = StructuralAgent(enable_memory=enable_memory)
        self._semantic = SemanticAgent(enable_memory=enable_memory)
        self._intent = IntentAgent(enable_memory=enable_memory)
        self._visual = VisualAgent(enable_memory=enable_memory)
        self._behavioral = BehavioralAgent(enable_memory=enable_memory)
        self._verdict = VerdictAgent(enable_memory=enable_memory)
        self._memory_agent = MemoryAgent(enable_memory=enable_memory)

        self._html_processor = HtmlProcessor()
        self._pdf_processor = PdfProcessor()
        self._image_processor = ImageProcessor()
        self._text_processor = TextProcessor()

    def scan(self, request: ScanRequest, job_id: str | None = None) -> ScanResult:
        job_id = job_id or str(uuid.uuid4())
        start_time = time.monotonic()

        try:
            processed_data = self._process_content(request.content, request.content_type)

            context: dict[str, Any] = {
                "content_type": request.content_type.value,
                "session_id": request.session_id,
                "metadata": request.metadata,
                "processed": processed_data,
            }

            findings = self._run_analysis_agents(request.content, context)

            context["agent_findings"] = findings
            verdict_finding = self._verdict.analyze(request.content, context)
            findings.append(verdict_finding)

            result = self._verdict.build_scan_result(
                job_id=job_id,
                content_type=request.content_type,
                findings=findings,
                processing_time_ms=int((time.monotonic() - start_time) * 1000),
            )

            self._memory_agent.analyze(
                request.content,
                {"scan_result": result, "session_id": request.session_id},
            )

            return result

        except Exception as exc:
            logger.error("Crew scan failed for job %s: %s", job_id, exc, exc_info=True)
            elapsed = int((time.monotonic() - start_time) * 1000)
            from aegis.core.constants import RiskLevel
            return ScanResult(
                job_id=job_id,
                risk_level=RiskLevel.SAFE,
                risk_score=0.0,
                is_injection=False,
                confidence=0.0,
                findings=[],
                summary=f"Analysis failed: {exc}",
                content_type=request.content_type,
                processing_time_ms=elapsed,
            )

    async def scan_async(self, request: ScanRequest, job_id: str | None = None) -> ScanResult:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(executor, self.scan, request, job_id)

    def _process_content(self, content: str, content_type: ContentType) -> dict[str, Any]:
        if content_type == ContentType.HTML:
            return self._html_processor.process(content).to_dict()
        elif content_type == ContentType.PDF:
            return self._pdf_processor.process(content).to_dict()
        elif content_type == ContentType.IMAGE:
            return self._image_processor.process(content).to_dict()
        else:
            return self._text_processor.process(content).to_dict()

    def _run_analysis_agents(self, content: str, context: dict[str, Any]) -> list[AgentFinding]:
        agents = [
            self._structural,
            self._semantic,
            self._intent,
            self._visual,
            self._behavioral,
        ]

        findings = []
        for agent in agents:
            try:
                finding = agent.analyze(content, context)
                findings.append(finding)
            except Exception as exc:
                logger.error("Agent %s failed: %s", agent.name, exc, exc_info=True)
                findings.append(AgentFinding(
                    agent=agent.name.value,
                    score=0.0,
                    signals=["agent_error"],
                    explanation=f"Agent failed: {exc}",
                ))

        return findings
