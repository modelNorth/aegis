"""Tests for session management endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_create_session_requires_auth(api_client: TestClient) -> None:
    response = api_client.post("/v1/sessions", json={})
    assert response.status_code == 401


def test_create_session_success(api_client: TestClient, test_api_key: str) -> None:
    response = api_client.post(
        "/v1/sessions",
        json={"user_id": "test-user"},
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["user_id"] == "test-user"


def test_create_session_without_user_id(api_client: TestClient, test_api_key: str) -> None:
    response = api_client.post(
        "/v1/sessions",
        json={},
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
