"""Job definitions and BullMQ queue setup."""

from __future__ import annotations

import logging
from typing import Any

from aegis.core.config import get_config

logger = logging.getLogger(__name__)

SCAN_QUEUE_NAME = "aegis-scan"
WEBHOOK_QUEUE_NAME = "aegis-webhook"
MEMORY_QUEUE_NAME = "aegis-memory"


class ScanQueue:
    def __init__(self) -> None:
        self._config = get_config()
        self._queue: Any | None = None

    def _get_connection_options(self) -> dict[str, Any]:
        import re
        url = self._config.redis.url
        match = re.match(r"redis://(?::(.+)@)?([^:/]+)(?::(\d+))?(?:/(\d+))?", url)
        if match:
            password, host, port, db = match.groups()
            return {
                "host": host or "localhost",
                "port": int(port or 6379),
                "db": int(db or 0),
                **({"password": password} if password else {}),
            }
        return {"host": "localhost", "port": 6379}

    def connect(self) -> None:
        try:
            from bullmq import Queue
            connection_opts = self._get_connection_options()
            self._queue = Queue(
                self._config.bullmq.queue_name,
                {"connection": connection_opts},
            )
            logger.info("BullMQ queue connected: %s", self._config.bullmq.queue_name)
        except Exception as exc:
            logger.warning("BullMQ queue init failed: %s", exc)
            self._queue = None

    async def add_scan_job(self, job_id: str, request_data: dict[str, Any]) -> str:
        if not self._queue:
            raise RuntimeError("Queue not connected")

        job_data = {
            "job_id": job_id,
            "request": request_data,
        }

        try:
            await self._queue.add(
                f"scan:{job_id}",
                job_data,
                {
                    "jobId": job_id,
                    "attempts": 3,
                    "backoff": {"type": "exponential", "delay": 5000},
                    "removeOnComplete": {"count": 100},
                    "removeOnFail": {"count": 50},
                },
            )
            return job_id
        except Exception as exc:
            raise RuntimeError(f"Failed to add scan job: {exc}") from exc

    async def close(self) -> None:
        if self._queue:
            try:
                await self._queue.close()
            except Exception:
                pass


_scan_queue: ScanQueue | None = None


def get_scan_queue() -> ScanQueue:
    global _scan_queue
    if _scan_queue is None:
        _scan_queue = ScanQueue()
        _scan_queue.connect()
    return _scan_queue
