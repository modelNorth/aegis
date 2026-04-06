"""Tests for health endpoint."""

import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


def test_health_includes_services(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], dict)
