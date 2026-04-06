"""Pydantic models for requests, responses, and domain objects."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from aegis.core.constants import ApiTier, ContentType, JobStatus, RiskLevel


class ScanRequest(BaseModel):
    content: str = Field(..., description="Content to scan (text, HTML, or base64-encoded for binary)")
    content_type: ContentType = Field(default=ContentType.TEXT, description="Type of content")
    session_id: str | None = Field(default=None, description="Session ID for context tracking")
    webhook_url: HttpUrl | None = Field(default=None, description="Webhook URL for async notifications")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    sync: bool = Field(default=False, description="If true, wait for result (max 30s)")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


class AgentFinding(BaseModel):
    agent: str = Field(..., description="Agent that produced the finding")
    score: float = Field(..., ge=0.0, le=1.0, description="Risk score 0-1")
    signals: list[str] = Field(default_factory=list, description="Detected signals")
    explanation: str = Field(default="", description="Human-readable explanation")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResult(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Aggregate risk score 0-1")
    is_injection: bool = Field(..., description="True if prompt injection detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict")
    findings: list[AgentFinding] = Field(default_factory=list, description="Per-agent findings")
    summary: str = Field(default="", description="Human-readable summary")
    content_type: ContentType
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sanitized_content: str | None = Field(default=None, description="Sanitized content after guardrails")


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime | None = None
    result: ScanResult | None = None
    error: str | None = None


class SessionCreateRequest(BaseModel):
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    user_id: str | None = None
    created_at: datetime
    scan_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionSummary(BaseModel):
    """Summary statistics for a session's scans."""

    session_id: str
    total_scans: int = 0
    injections_detected: int = 0
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    avg_risk_score: float = 0.0
    top_agents_triggered: list[tuple[str, int]] = Field(default_factory=list)
    scan_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None
    last_scan_at: datetime | None = None


class FeedbackRequest(BaseModel):
    job_id: str = Field(..., description="Job ID to provide feedback for")
    is_correct: bool = Field(..., description="Whether the verdict was correct")
    actual_risk_level: RiskLevel | None = Field(default=None, description="Correct risk level if wrong")
    notes: str | None = Field(default=None, description="Optional notes")


class FeedbackResponse(BaseModel):
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    accepted: bool = True
    message: str = "Feedback recorded"


class ApiKey(BaseModel):
    key_id: str
    api_key: str
    tier: ApiTier
    user_id: str
    created_at: datetime
    is_active: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
