"""Aggregated statistics and monitoring metrics endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Analysis
from app.schemas.stats import AnalysisStatsResponse

router = APIRouter(prefix="/analyses", tags=["Statistics"])


@router.get(
    "/stats",
    response_model=AnalysisStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Statistics",
    description="Retrieve aggregate metrics including total analyses, breakdown by status, and breakdown by disease class.",
)
def get_analysis_statistics(db: Session = Depends(get_db)) -> AnalysisStatsResponse:
    """Compute and return aggregate analysis metrics."""
    # 1. Total analyses count
    total_analyses = db.scalar(select(func.count(Analysis.id))) or 0

    # 2. Counts grouped by status
    status_query = select(Analysis.status, func.count(Analysis.id)).group_by(Analysis.status)
    status_rows = db.execute(status_query).all()
    counts_by_status = {str(status_name): count for status_name, count in status_rows}

    # 3. Counts grouped by predicted class (only for non-null classes)
    class_query = (
        select(Analysis.predicted_class, func.count(Analysis.id))
        .where(Analysis.predicted_class.isnot(None))
        .group_by(Analysis.predicted_class)
    )
    class_rows = db.execute(class_query).all()
    counts_by_class = {str(cls_name): count for cls_name, count in class_rows}

    # 4. Count of analyses in the last 24 hours
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_query = select(func.count(Analysis.id)).where(Analysis.created_at >= since_24h)
    analyses_last_24h = db.scalar(recent_query) or 0

    return AnalysisStatsResponse(
        total_analyses=total_analyses,
        counts_by_status=counts_by_status,
        counts_by_class=counts_by_class,
        analyses_last_24h=analyses_last_24h,
    )
