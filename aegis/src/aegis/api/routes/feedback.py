"""Training feedback endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from aegis.api.deps import AuthDep
from aegis.core.exceptions import StorageError
from aegis.core.models import FeedbackRequest, FeedbackResponse
from aegis.storage.supabase import get_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest,
    api_key_data: AuthDep,
) -> FeedbackResponse:
    key_id = api_key_data.get("key_id", "unknown")

    try:
        store = get_store()
        job = await store.get_job(request.job_id)
    except Exception as exc:
        logger.warning("Job not found for feedback: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {request.job_id} not found",
        )

    try:
        feedback_id = await store.store_feedback(request, key_id)

        from aegis.agents.memory_agent import MemoryAgent
        memory_agent = MemoryAgent(enable_memory=True)
        memory_agent.update_from_feedback(
            job_id=request.job_id,
            is_correct=request.is_correct,
            actual_risk_level=request.actual_risk_level.value if request.actual_risk_level else None,
        )

        return FeedbackResponse(
            feedback_id=feedback_id,
            job_id=request.job_id,
            accepted=True,
            message="Feedback recorded and memory updated",
        )
    except StorageError as exc:
        logger.error("Failed to store feedback: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store feedback")
