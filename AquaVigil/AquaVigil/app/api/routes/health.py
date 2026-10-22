"""Health and operational diagnostic endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.health import HealthResponse
from app.services.prediction_service import prediction_engine

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Check the operational readiness of the API, database connectivity, and ML model status.",
)
def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Return health status of API, database, and inference engine."""
    # Verify database connection
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Verify model engine state
    model_status = prediction_engine.get_status_label()

    overall_status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        database=db_status,
        model_status=model_status,
        timestamp=datetime.now(timezone.utc),
    )
