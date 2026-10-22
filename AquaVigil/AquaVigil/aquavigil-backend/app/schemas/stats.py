"""Pydantic schemas for analysis statistics and aggregate dashboard metrics."""

from typing import Dict
from pydantic import BaseModel, Field


class AnalysisStatsResponse(BaseModel):
    """Aggregate statistics across all fish disease analyses."""
    total_analyses: int = Field(..., description="Total number of image analyses performed", ge=0)
    counts_by_status: Dict[str, int] = Field(
        ...,
        description="Analysis count grouped by status ('completed', 'model_not_configured', 'failed')"
    )
    counts_by_class: Dict[str, int] = Field(
        ...,
        description="Analysis count grouped by predicted fish disease class"
    )
    analyses_last_24h: int = Field(..., description="Analyses submitted in the last 24 hours", ge=0)
