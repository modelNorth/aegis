"""Session management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from aegis.api.deps import AuthDep
from aegis.core.exceptions import StorageError
from aegis.core.models import SessionCreateRequest, SessionResponse
from aegis.storage.supabase import get_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    api_key_data: AuthDep,
) -> SessionResponse:
    try:
        store = get_store()
        session = await store.create_session(
            user_id=request.user_id,
            metadata=request.metadata,
        )
        return session
    except StorageError as exc:
        logger.error("Failed to create session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    api_key_data: AuthDep,
) -> SessionResponse:
    try:
        store = get_store()
        response = store.client.table("sessions").select("*").eq("id", session_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        row = response.data[0]
        from datetime import datetime
        return SessionResponse(
            session_id=row["id"],
            user_id=row.get("user_id"),
            created_at=datetime.fromisoformat(row["created_at"]),
            scan_count=row.get("scan_count", 0),
            metadata=row.get("metadata", {}),
        )
    except HTTPException:
        raise
    except StorageError as exc:
        logger.error("Storage error: %s", exc)
        raise HTTPException(status_code=500, detail="Storage error")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    api_key_data: AuthDep,
) -> None:
    try:
        store = get_store()
        store.client.table("sessions").delete().eq("id", session_id).execute()
    except StorageError as exc:
        logger.error("Failed to delete session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete session")
