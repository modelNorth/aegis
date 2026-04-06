"""Telemetry and observability using Langfuse."""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar

from aegis.core.config import get_config

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class LangfuseClient:
    """Langfuse telemetry client with graceful fallback."""

    _instance: LangfuseClient | None = None

    def __new__(cls) -> LangfuseClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized: bool = False
            cls._instance._client: Any | None = None
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._init_client()

    def _init_client(self) -> None:
        config = get_config()
        if not config.langfuse.enabled or not config.langfuse.public_key:
            logger.info("Langfuse telemetry disabled (no configuration)")
            return

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=config.langfuse.public_key,
                secret_key=config.langfuse.secret_key or "",
                host=config.langfuse.host or "https://cloud.langfuse.com",
            )
            logger.info("Langfuse telemetry initialized")
        except Exception as exc:
            logger.warning("Failed to initialize Langfuse: %s", exc)
            self._client = None

    @property
    def is_enabled(self) -> bool:
        return self._client is not None

    def create_trace(
        self,
        name: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any | None:
        """Create a new trace."""
        if not self._client:
            return None
        try:
            return self._client.trace(name=name, user_id=user_id, metadata=metadata)
        except Exception as exc:
            logger.debug("Failed to create trace: %s", exc)
            return None

    def create_span(
        self,
        trace: Any,
        name: str,
        input_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any | None:
        """Create a span within a trace."""
        if not trace:
            return None
        try:
            return trace.span(name=name, input=input_data, metadata=metadata)
        except Exception as exc:
            logger.debug("Failed to create span: %s", exc)
            return None

    def finalize_span(
        self,
        span: Any,
        output_data: Any = None,
        metadata: dict[str, Any] | None = None,
        level: str | None = None,
    ) -> None:
        """Finalize a span with output data."""
        if not span:
            return
        try:
            kwargs: dict[str, Any] = {"output": output_data}
            if metadata:
                kwargs["metadata"] = metadata
            if level:
                kwargs["level"] = level
            span.end(**kwargs)
        except Exception as exc:
            logger.debug("Failed to finalize span: %s", exc)


def get_langfuse() -> LangfuseClient:
    """Get the Langfuse client singleton."""
    return LangfuseClient()


@contextmanager
def trace_span(
    trace_name: str,
    span_name: str,
    user_id: str | None = None,
    input_data: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Context manager for creating a trace and span."""
    langfuse = get_langfuse()
    trace = langfuse.create_trace(trace_name, user_id=user_id, metadata=metadata)
    span = langfuse.create_span(trace, span_name, input_data=input_data)
    try:
        yield span
    finally:
        if span:
            langfuse.finalize_span(span)


def traced(
    name: str | None = None,
    trace_name: str | None = None,
) -> Callable[[F], F]:
    """Decorator to trace a function execution."""

    def decorator(func: F) -> F:
        span_name = name or func.__name__
        _trace_name = trace_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            langfuse = get_langfuse()
            if not langfuse.is_enabled:
                return func(*args, **kwargs)

            trace = langfuse.create_trace(_trace_name)
            span = langfuse.create_span(trace, span_name, input_data={"args": str(args), "kwargs": list(kwargs.keys())})

            try:
                result = func(*args, **kwargs)
                if span:
                    langfuse.finalize_span(span, output_data={"result_type": type(result).__name__})
                return result
            except Exception as exc:
                if span:
                    langfuse.finalize_span(span, output_data={"error": str(exc)}, level="ERROR")
                raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            langfuse = get_langfuse()
            if not langfuse.is_enabled:
                return await func(*args, **kwargs)

            trace = langfuse.create_trace(_trace_name)
            span = langfuse.create_span(trace, span_name, input_data={"args": str(args), "kwargs": list(kwargs.keys())})

            try:
                result = await func(*args, **kwargs)
                if span:
                    langfuse.finalize_span(span, output_data={"result_type": type(result).__name__})
                return result
            except Exception as exc:
                if span:
                    langfuse.finalize_span(span, output_data={"error": str(exc)}, level="ERROR")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator
