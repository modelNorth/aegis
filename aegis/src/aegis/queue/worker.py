"""BullMQ worker process for async scan job processing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import structlog

from aegis.core.config import get_config
from aegis.core.constants import JobStatus
from aegis.core.models import ScanRequest

logger = structlog.get_logger(__name__)


class ScanWorker:
    def __init__(self) -> None:
        self._config = get_config()
        self._worker: Any | None = None
        self._running = False

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

    async def process_job(self, job: Any, job_token: str | None = None) -> dict[str, Any]:
        job_id = job.data.get("job_id")
        request_data = job.data.get("request", {})

        logger.info("processing_scan_job", job_id=job_id)

        try:
            from aegis.storage.supabase import get_store
            store = get_store()
            await store.update_job_status(job_id, JobStatus.PROCESSING)
        except Exception as exc:
            logger.warning("Could not update job status", error=str(exc))

        try:
            request = ScanRequest(**request_data)

            from aegis.agents.crew import AegisCrew
            crew = AegisCrew()
            result = await crew.scan_async(request, job_id)

            try:
                from aegis.storage.supabase import get_store
                store = get_store()
                await store.update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    result=result.model_dump(mode="json"),
                )
            except Exception as exc:
                logger.warning("Failed to store job result", job_id=job_id, error=str(exc))

            if request.webhook_url:
                from aegis.queue.webhooks import deliver_webhook
                await deliver_webhook(str(request.webhook_url), job_id, result)

            logger.info(
                "scan_job_completed",
                job_id=job_id,
                risk_level=result.risk_level.value,
                is_injection=result.is_injection,
            )
            return result.model_dump(mode="json")

        except Exception as exc:
            logger.error("scan_job_failed", job_id=job_id, error=str(exc), exc_info=True)
            try:
                from aegis.storage.supabase import get_store
                store = get_store()
                await store.update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            except Exception:
                pass
            raise

    def start(self) -> None:
        try:
            from bullmq import Worker
            connection_opts = self._get_connection_options()
            self._worker = Worker(
                self._config.bullmq.queue_name,
                self.process_job,
                {"connection": connection_opts},
            )
            self._running = True
            logger.info("scan_worker_started", queue=self._config.bullmq.queue_name)
        except Exception as exc:
            logger.error("worker_start_failed", error=str(exc))
            raise

    async def run_forever(self) -> None:
        self.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("worker_stopping")
        finally:
            await self.stop()

    async def stop(self) -> None:
        self._running = False
        if self._worker:
            try:
                await self._worker.close()
            except Exception as exc:
                logger.warning("worker_stop_error", error=str(exc))


async def run_worker() -> None:
    worker = ScanWorker()
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(run_worker())
