"""Tests for analysis statistics and aggregate dashboard metrics."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Analysis


def test_statistics_empty_database(client: TestClient):
    """Verify statistics return zeroed aggregate metrics on an empty database."""
    response = client.get("/api/v1/analyses/stats")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_analyses"] == 0
    assert data["counts_by_status"] == {}
    assert data["counts_by_class"] == {}
    assert data["analyses_last_24h"] == 0


def test_statistics_populated_database(client: TestClient, db_session: Session):
    """Verify statistics accurately count records grouped by status and predicted disease."""
    # Seed mock records directly in DB
    rec1 = Analysis(
        original_filename="sample1.jpg",
        stored_filename="s1.jpg",
        file_path="/tmp/s1.jpg",
        file_size_bytes=1000,
        mime_type="image/jpeg",
        status="completed",
        predicted_class="Ichthyophthiriasis (White Spot)",
        confidence=0.92,
    )
    rec2 = Analysis(
        original_filename="sample2.jpg",
        stored_filename="s2.jpg",
        file_path="/tmp/s2.jpg",
        file_size_bytes=1200,
        mime_type="image/jpeg",
        status="completed",
        predicted_class="Ichthyophthiriasis (White Spot)",
        confidence=0.88,
    )
    rec3 = Analysis(
        original_filename="sample3.jpg",
        stored_filename="s3.jpg",
        file_path="/tmp/s3.jpg",
        file_size_bytes=900,
        mime_type="image/jpeg",
        status="model_not_configured",
        predicted_class=None,
        confidence=None,
    )
    rec4 = Analysis(
        original_filename="sample4.jpg",
        stored_filename="s4.jpg",
        file_path="/tmp/s4.jpg",
        file_size_bytes=800,
        mime_type="image/jpeg",
        status="failed",
        predicted_class=None,
        error_message="Blurry image",
    )

    db_session.add_all([rec1, rec2, rec3, rec4])
    db_session.commit()

    response = client.get("/api/v1/analyses/stats")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_analyses"] == 4
    assert data["counts_by_status"]["completed"] == 2
    assert data["counts_by_status"]["model_not_configured"] == 1
    assert data["counts_by_status"]["failed"] == 1
    assert data["counts_by_class"]["Ichthyophthiriasis (White Spot)"] == 2
    assert data["analyses_last_24h"] == 4
