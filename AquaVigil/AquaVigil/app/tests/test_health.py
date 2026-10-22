"""Tests for health check and root endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verify root endpoint returns project metadata and navigation links."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "project" in data
    assert "documentation" in data
    assert data["documentation"] == "/docs"


def test_health_check_endpoint(client: TestClient):
    """Verify /health endpoint returns service health and dependencies status."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["model_status"] in {"not_configured", "mock_mode", "ready"}
    assert "version" in data
    assert "timestamp" in data


def test_api_v1_health_check_endpoint(client: TestClient):
    """Verify /api/v1/health returns consistent status."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
