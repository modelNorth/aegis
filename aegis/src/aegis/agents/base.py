"""Base agent class with Mem0 memory integration."""

from __future__ import annotations

import logging
from typing import Any

from aegis.core.config import get_config
from aegis.core.constants import AgentName
from aegis.core.models import AgentFinding

logger = logging.getLogger(__name__)


class BaseAegisAgent:
    name: AgentName
    role: str
    goal: str
    backstory: str

    def __init__(self, enable_memory: bool = True) -> None:
        self._config = get_config()
        self._memory_client: Any | None = None
        self._enable_memory = enable_memory
        if enable_memory:
            self._init_memory()

    def _init_memory(self) -> None:
        try:
            from mem0 import Memory

            mem0_config = self._build_mem0_config()
            self._memory_client = Memory.from_config(mem0_config)
        except Exception as exc:
            logger.warning("Mem0 memory init failed for agent %s: %s", self.name, exc)
            self._memory_client = None

    def _build_mem0_config(self) -> dict[str, Any]:
        config = get_config()
        mem0_cfg: dict[str, Any] = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": config.openai.model,
                    "api_key": config.openai.api_key,
                },
            },
        }

        if config.mem0.qdrant_host:
            mem0_cfg["vector_store"] = {
                "provider": "qdrant",
                "config": {
                    "host": config.mem0.qdrant_host,
                    "port": config.mem0.qdrant_port,
                    "collection_name": f"aegis_{self.name.value}",
                },
            }
        elif config.mem0.api_key:
            mem0_cfg["api_key"] = config.mem0.api_key

        return mem0_cfg

    def add_memory(self, content: str, user_id: str = "aegis-system", metadata: dict | None = None) -> None:
        if not self._memory_client:
            return
        try:
            self._memory_client.add(
                content,
                user_id=user_id,
                metadata={"agent": self.name.value, **(metadata or {})},
            )
        except Exception as exc:
            logger.debug("Memory add failed for agent %s: %s", self.name, exc)

    def search_memory(self, query: str, user_id: str = "aegis-system", limit: int = 5) -> list[dict]:
        if not self._memory_client:
            return []
        try:
            results = self._memory_client.search(query, user_id=user_id, limit=limit)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.debug("Memory search failed for agent %s: %s", self.name, exc)
            return []

    def analyze(self, content: str, context: dict[str, Any]) -> AgentFinding:
        raise NotImplementedError("Subclasses must implement analyze()")

    def _make_finding(
        self,
        score: float,
        signals: list[str],
        explanation: str,
        metadata: dict | None = None,
    ) -> AgentFinding:
        return AgentFinding(
            agent=self.name.value,
            score=round(score, 4),
            signals=signals,
            explanation=explanation,
            metadata=metadata or {},
        )
