"""Pydantic schema for health check endpoint."""

from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status and diagnostic details of the backend service."""
    status: str = Field(..., description="Overall service status (e.g., 'healthy')")
    service: str = Field(..., description="Service application name")
    version: str = Field(..., description="Semantic API version")
    database: str = Field(..., description="Database connection status ('connected' or 'disconnected')")
    model_status: str = Field(
        ...,
        description="Status of AI inference model: 'ready', 'not_configured', or 'mock_mode'"
    )
    timestamp: datetime = Field(..., description="Current UTC timestamp of the health check")
