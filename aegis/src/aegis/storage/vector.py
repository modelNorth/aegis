"""Vector storage operations for semantic search via Supabase pgvector."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from aegis.core.config import get_config
from aegis.core.exceptions import StorageError
from aegis.storage.supabase import get_store

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self._config = get_config()
        self._model: Any | None = None

    def _load_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._config.processing.embedding_model)
            return True
        except Exception as exc:
            logger.warning("Failed to load embedding model: %s", exc)
            return False

    def embed(self, text: str) -> list[float] | None:
        if not self._load_model():
            return None
        try:
            embedding = self._model.encode([text[:512]], convert_to_numpy=True, normalize_embeddings=True)
            return embedding[0].tolist()
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return None

    async def store_scan_embedding(self, job_id: str, content: str, metadata: dict[str, Any]) -> bool:
        embedding = self.embed(content[:512])
        if not embedding:
            return False

        try:
            store = get_store()
            store.client.table("scan_embeddings").insert({
                "job_id": job_id,
                "embedding": embedding,
                "metadata": metadata,
            }).execute()
            return True
        except Exception as exc:
            logger.warning("Failed to store embedding for job %s: %s", job_id, exc)
            return False

    async def search_similar(self, query: str, limit: int = 10, threshold: float = 0.8) -> list[dict[str, Any]]:
        embedding = self.embed(query)
        if not embedding:
            return []

        try:
            store = get_store()
            response = store.client.rpc(
                "match_scan_embeddings",
                {
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": limit,
                },
            ).execute()
            return response.data or []
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
