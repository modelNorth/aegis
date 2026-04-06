"""Scan endpoints - POST /v1/scan, GET /v1/scan/{job_id}."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from aegis.api.deps import AuthDep
from aegis.core.config import get_config
from aegis.core.constants import ContentType, JobStatus
from aegis.core.exceptions import FileTooLargeError, JobNotFoundError, StorageError
from aegis.core.models import JobResponse, ScanRequest, ScanResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/scan", tags=["scan"])


def _get_crew() -> Any:
    from aegis.agents.crew import AegisCrew
    return AegisCrew()


def _get_store() -> Any:
    from aegis.storage.supabase import get_store
    return get_store()


def _get_queue() -> Any:
    from aegis.queue.jobs import get_scan_queue
    return get_scan_queue()


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    api_key_data: AuthDep,
) -> JobResponse:
    config = get_config()

    content_bytes = len(request.content.encode("utf-8"))
    max_bytes = config.max_file_size_bytes
    if content_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content size {content_bytes / 1024 / 1024:.1f}MB exceeds {config.processing.max_file_size_mb}MB limit",
        )

    job_id = str(uuid.uuid4())

    if request.sync:
        try:
            result = await _run_scan_sync(request, job_id)
            return JobResponse(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                created_at=result.created_at,
                updated_at=result.created_at,
                result=result,
            )
        except Exception as exc:
            logger.error("Sync scan failed for job %s: %s", job_id, exc)
            raise HTTPException(status_code=500, detail=str(exc))

    background_tasks.add_task(_run_scan_background, request, job_id)

    from datetime import datetime
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_scan(
    job_id: str,
    api_key_data: AuthDep,
) -> JobResponse:
    try:
        store = _get_store()
        job = await store.get_job(job_id)
        return job
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    except StorageError as exc:
        logger.error("Storage error fetching job %s: %s", job_id, exc)
        raise HTTPException(status_code=500, detail="Storage error")


async def _run_scan_sync(request: ScanRequest, job_id: str) -> ScanResult:
    loop = asyncio.get_event_loop()
    crew = _get_crew()

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, crew.scan, request, job_id)


async def _run_scan_background(request: ScanRequest, job_id: str) -> None:
    try:
        store = _get_store()
        await store.update_job_status(job_id, JobStatus.PROCESSING)
    except Exception as exc:
        logger.warning("Could not update job status to processing: %s", exc)

    try:
        crew = _get_crew()
        result = await crew.scan_async(request, job_id)

        try:
            store = _get_store()
            await store.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                result=result.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.warning("Could not store job result: %s", exc)

        if request.webhook_url:
            from aegis.queue.webhooks import deliver_webhook
            await deliver_webhook(str(request.webhook_url), job_id, result)

    except Exception as exc:
        logger.error("Background scan failed for job %s: %s", job_id, exc)
        try:
            store = _get_store()
            await store.update_job_status(job_id, JobStatus.FAILED, error=str(exc))
        except Exception:
            pass
