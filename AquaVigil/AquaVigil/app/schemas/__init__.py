"""Schemas package for AquaVigil Backend."""

from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisResponse,
    BoundingBox,
    DeleteResponse,
    ExplanationResponse,
    ImageDimensions,
)
from app.schemas.health import HealthResponse
from app.schemas.stats import AnalysisStatsResponse

__all__ = [
    "AnalysisListResponse",
    "AnalysisResponse",
    "BoundingBox",
    "DeleteResponse",
    "ExplanationResponse",
    "ImageDimensions",
    "HealthResponse",
    "AnalysisStatsResponse",
]
