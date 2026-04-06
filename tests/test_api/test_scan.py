"""Tests for scan API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_scan_requires_api_key(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/scan",
        json={"content": "test content", "content_type": "text"},
    )
    assert response.status_code == 401


def test_scan_with_api_key_accepted(api_client: TestClient, test_api_key: str) -> None:
    response = api_client.post(
        "/v1/scan",
        json={"content": "Hello world, normal text.", "content_type": "text"},
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code in (200, 202)
    data = response.json()
    assert "job_id" in data
    assert "status" in data


def test_scan_sync_returns_result(api_client: TestClient, test_api_key: str) -> None:
    response = api_client.post(
        "/v1/scan",
        json={
            "content": "The sky is blue and birds are singing.",
            "content_type": "text",
            "sync": True,
        },
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code in (200, 202)
    data = response.json()
    assert "job_id" in data


def test_scan_rejects_empty_content(api_client: TestClient, test_api_key: str) -> None:
    response = api_client.post(
        "/v1/scan",
        json={"content": "", "content_type": "text"},
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code == 422


def test_scan_html_content_type(api_client: TestClient, test_api_key: str) -> None:
    html = "<html><body><p>Hello World</p></body></html>"
    response = api_client.post(
        "/v1/scan",
        json={"content": html, "content_type": "html"},
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code in (200, 202)


def test_get_scan_not_found(api_client: TestClient, test_api_key: str) -> None:
    import uuid
    response = api_client.get(
        f"/v1/scan/{uuid.uuid4()}",
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code in (200, 404)


def test_get_scan_requires_api_key(api_client: TestClient) -> None:
    response = api_client.get("/v1/scan/some-job-id")
    assert response.status_code == 401


def test_scan_with_session_id(api_client: TestClient, test_api_key: str) -> None:
    import uuid
    session_id = str(uuid.uuid4())
    response = api_client.post(
        "/v1/scan",
        json={
            "content": "Some content to scan",
            "content_type": "text",
            "session_id": session_id,
        },
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code in (200, 202)
