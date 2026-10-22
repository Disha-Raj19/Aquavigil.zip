"""Comprehensive test suite for fish disease image analysis endpoints."""

import io
from PIL import Image
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Analysis
from app.services.prediction_service import BasePredictionEngine, PredictionResult


def test_upload_valid_jpeg(client: TestClient, sample_jpeg_bytes: bytes):
    """Test uploading a valid JPEG image."""
    files = {"file": ("test_fish.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["analysis_id"] is not None
    assert data["original_filename"] == "test_fish.jpg"
    assert data["mime_type"] == "image/jpeg"
    assert data["image_dimensions"]["width"] == 120
    assert data["image_dimensions"]["height"] == 80
    assert data["status"] == "model_not_configured"
    assert data["predicted_class"] is None
    assert data["confidence"] is None
    assert data["explanation_available"] is False


def test_upload_valid_png_converts_to_rgb(client: TestClient, sample_png_bytes: bytes):
    """Test uploading a valid PNG image (RGBA) and verify dimensions."""
    files = {"file": ("sample_salmon.png", sample_png_bytes, "image/png")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["analysis_id"] is not None
    assert data["original_filename"] == "sample_salmon.png"
    assert data["mime_type"] == "image/png"
    assert data["image_dimensions"]["width"] == 150
    assert data["image_dimensions"]["height"] == 100


def test_upload_corrupted_image(client: TestClient, corrupted_image_bytes: bytes):
    """Test rejection of corrupted image bytes with image/jpeg extension."""
    files = {"file": ("corrupt_fish.jpg", corrupted_image_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "corrupted or not a valid image" in data["detail"].lower()


def test_upload_unsupported_media_type(client: TestClient):
    """Test rejection of unsupported file formats (e.g. text or pdf)."""
    files = {"file": ("notes.pdf", b"%PDF-1.4...", "application/pdf")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    data = response.json()
    assert "unsupported media type" in data["detail"].lower()


def test_upload_oversized_file(client: TestClient, monkeypatch):
    """Test rejection of file exceeding the configured size limit."""
    # Temporarily set max upload to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    # 1.1 MB buffer of zeros
    oversized_data = b"0" * (1 * 1024 * 1024 + 1024)
    files = {"file": ("giant_fish.jpg", oversized_data, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == (status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413)
    data = response.json()
    assert "exceeds the maximum allowed limit" in data["detail"].lower()


def test_upload_empty_file(client: TestClient):
    """Test rejection of an empty (0 byte) file."""
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "empty" in data["detail"].lower()


def test_analysis_persistence_in_db(client: TestClient, sample_jpeg_bytes: bytes, db_session: Session):
    """Verify that uploading an image creates a complete database record."""
    files = {"file": ("carp_sample.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)
    assert response.status_code == status.HTTP_201_CREATED
    analysis_id = response.json()["analysis_id"]

    # Query DB directly to verify persistence
    record = db_session.get(Analysis, analysis_id)
    assert record is not None
    assert record.original_filename == "carp_sample.jpg"
    assert record.image_width == 120
    assert record.image_height == 80
    assert record.stored_filename.endswith(".jpg")
    assert record.status == "model_not_configured"


def test_get_analysis_by_id(client: TestClient, sample_jpeg_bytes: bytes):
    """Test retrieval of a specific analysis record by ID."""
    files = {"file": ("fish_retrieval.jpg", sample_jpeg_bytes, "image/jpeg")}
    upload_res = client.post("/api/v1/analyses", files=files)
    analysis_id = upload_res.json()["analysis_id"]

    response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["analysis_id"] == analysis_id
    assert data["original_filename"] == "fish_retrieval.jpg"


def test_get_nonexistent_analysis_returns_404(client: TestClient):
    """Test 404 response when querying a non-existent analysis ID."""
    response = client.get("/api/v1/analyses/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "was not found" in response.json()["detail"].lower()


def test_list_analyses_pagination(client: TestClient, sample_jpeg_bytes: bytes):
    """Test paginated retrieval of analyses history."""
    # Upload 3 distinct samples
    for i in range(3):
        files = {"file": (f"fish_{i}.jpg", sample_jpeg_bytes, "image/jpeg")}
        client.post("/api/v1/analyses", files=files)

    # Fetch page 1 with limit 2
    res_page1 = client.get("/api/v1/analyses?limit=2&offset=0")
    assert res_page1.status_code == status.HTTP_200_OK
    data_page1 = res_page1.json()
    assert data_page1["total"] >= 3
    assert len(data_page1["items"]) == 2
    assert data_page1["limit"] == 2
    assert data_page1["offset"] == 0

    # Fetch page 2 with limit 2, offset 2
    res_page2 = client.get("/api/v1/analyses?limit=2&offset=2")
    assert res_page2.status_code == status.HTTP_200_OK
    data_page2 = res_page2.json()
    assert len(data_page2["items"]) >= 1


def test_explanation_endpoint_when_unavailable(client: TestClient, sample_jpeg_bytes: bytes):
    """Verify 409 Conflict when explanation is requested on an analysis without explanation."""
    files = {"file": ("no_gradcam.jpg", sample_jpeg_bytes, "image/jpeg")}
    upload_res = client.post("/api/v1/analyses", files=files)
    analysis_id = upload_res.json()["analysis_id"]

    response = client.get(f"/api/v1/analyses/{analysis_id}/explanation")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "no visual explanation" in response.json()["detail"].lower()


def test_explanation_endpoint_404_for_missing_record(client: TestClient):
    """Verify 404 when requesting explanation for a nonexistent analysis ID."""
    response = client.get("/api/v1/analyses/999999/explanation")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_prediction_error_handling(client: TestClient, sample_jpeg_bytes: bytes, monkeypatch):
    """Verify that an inference failure records status 'failed' without crashing API."""
    class FailingEngine(BasePredictionEngine):
        def predict(self, image: Image.Image) -> PredictionResult:
            return PredictionResult(
                status="failed",
                predicted_class=None,
                confidence=None,
                explanation_available=False,
                error_message="Simulated GPU CUDA out of memory error during inference.",
            )

        def is_ready(self) -> bool:
            return True

        def get_status_label(self) -> str:
            return "ready"

    from app.api.routes import analysis as analysis_module
    monkeypatch.setattr(analysis_module, "prediction_engine", FailingEngine())

    files = {"file": ("failing_inference.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "failed"
    assert data["predicted_class"] is None
    assert data["confidence"] is None
    assert "cuda out of memory" in data["error_message"].lower()


def test_delete_analysis_record_and_file(client: TestClient, sample_jpeg_bytes: bytes):
    """Verify safe deletion of analysis record and associated stored image."""
    files = {"file": ("to_delete.jpg", sample_jpeg_bytes, "image/jpeg")}
    upload_res = client.post("/api/v1/analyses", files=files)
    analysis_id = upload_res.json()["analysis_id"]

    # Delete record
    del_res = client.delete(f"/api/v1/analyses/{analysis_id}")
    assert del_res.status_code == status.HTTP_200_OK
    assert del_res.json()["success"] is True

    # Confirm 404 when re-fetching
    get_res = client.get(f"/api/v1/analyses/{analysis_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND

    # Deleting again should return 404
    del_again_res = client.delete(f"/api/v1/analyses/{analysis_id}")
    assert del_again_res.status_code == status.HTTP_404_NOT_FOUND


def test_download_analysis_image(client: TestClient, sample_jpeg_bytes: bytes):
    """Verify downloading original image from /analyses/{id}/image."""
    files = {"file": ("download_test.jpg", sample_jpeg_bytes, "image/jpeg")}
    upload_res = client.post("/api/v1/analyses", files=files)
    analysis_id = upload_res.json()["analysis_id"]

    img_res = client.get(f"/api/v1/analyses/{analysis_id}/image")
    assert img_res.status_code == status.HTTP_200_OK
    assert img_res.headers["content-type"] == "image/jpeg"
    assert len(img_res.content) > 0


def test_mock_mode_behavior(client: TestClient, sample_jpeg_bytes: bytes, monkeypatch):
    """Verify that when mock mode is explicitly enabled, output is visibly marked as simulated."""
    from app.services.prediction_service import MockPredictionEngine
    from app.api.routes import analysis as analysis_module

    monkeypatch.setattr(analysis_module, "prediction_engine", MockPredictionEngine())

    files = {"file": ("mock_fish.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyses", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "completed"
    assert "[SIMULATED]" in data["predicted_class"]
    assert data["confidence"] == 0.85
    assert data["explanation_available"] is True
    assert data["bounding_boxes"] is not None

