"""Webhook delivery system with exponential backoff retries."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from aegis.core.config import get_config
from aegis.core.models import ScanResult

logger = logging.getLogger(__name__)


def _sign_payload(payload: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=False,
)
async def deliver_webhook(url: str, job_id: str, result: ScanResult) -> bool:
    config = get_config()

    payload_data = {
        "event": "scan.completed",
        "job_id": job_id,
        "timestamp": time.time(),
        "result": result.model_dump(mode="json"),
    }
    payload_bytes = json.dumps(payload_data, default=str).encode("utf-8")

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "Aegis-Webhook/1.0",
        "X-Aegis-Job-ID": job_id,
    }

    if config.webhook.secret:
        headers["X-Aegis-Signature"] = _sign_payload(payload_bytes, config.webhook.secret)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, content=payload_bytes, headers=headers)
            response.raise_for_status()
            logger.info("Webhook delivered to %s (status=%d)", url, response.status_code)
            return True
    except httpx.HTTPStatusError as exc:
        logger.warning("Webhook failed with HTTP %d: %s", exc.response.status_code, url)
        raise
    except Exception as exc:
        logger.warning("Webhook delivery error: %s", exc)
        raise
