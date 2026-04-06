"""Custom exceptions for Aegis."""

from typing import Any


class AegisError(Exception):
    """Base exception for all Aegis errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AegisError):
    """Raised when authentication fails."""


class AuthorizationError(AegisError):
    """Raised when authorization fails."""


class RateLimitError(AegisError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(AegisError):
    """Raised when input validation fails."""


class FileTooLargeError(AegisError):
    """Raised when uploaded file exceeds size limit."""

    def __init__(self, max_size_mb: int, actual_size_mb: float) -> None:
        super().__init__(
            f"File size {actual_size_mb:.1f}MB exceeds maximum {max_size_mb}MB",
            {"max_size_mb": max_size_mb, "actual_size_mb": actual_size_mb},
        )


class UnsupportedContentTypeError(AegisError):
    """Raised when content type is not supported."""


class ProcessingError(AegisError):
    """Raised when content processing fails."""


class ProcessingTimeoutError(ProcessingError):
    """Raised when content processing times out."""


class AgentError(AegisError):
    """Raised when a CrewAI agent fails."""

    def __init__(self, agent_name: str, message: str) -> None:
        super().__init__(f"Agent '{agent_name}' failed: {message}", {"agent": agent_name})
        self.agent_name = agent_name


class StorageError(AegisError):
    """Raised when storage operations fail."""


class JobNotFoundError(AegisError):
    """Raised when a job is not found."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' not found", {"job_id": job_id})
        self.job_id = job_id


class WebhookError(AegisError):
    """Raised when webhook delivery fails."""


class ConfigurationError(AegisError):
    """Raised when configuration is invalid."""
