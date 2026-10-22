"""Pydantic schemas for fish disease analysis requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImageDimensions(BaseModel):
    """Dimensions of the uploaded fish image in pixels."""
    width: int = Field(..., description="Image width in pixels", ge=1)
    height: int = Field(..., description="Image height in pixels", ge=1)


class BoundingBox(BaseModel):
    """Optional bounding box for detected symptomatic region on fish."""
    box: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]")
    label: str = Field(..., description="Predicted label for the region")
    confidence: float = Field(..., description="Confidence score for this detection", ge=0.0, le=1.0)


class AnalysisResponse(BaseModel):
    """Detailed response schema for a fish image analysis record."""
    analysis_id: int = Field(..., description="Unique database identifier for the analysis")
    status: str = Field(
        ...,
        description="Current state of analysis: 'completed', 'model_not_configured', 'failed', or 'pending'"
    )
    predicted_class: Optional[str] = Field(
        default=None,
        description="Predicted fish disease or 'healthy', null when model is not configured"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Model confidence score between 0.0 and 1.0, null when model is not configured"
    )
    image_dimensions: Optional[ImageDimensions] = Field(
        default=None,
        description="Width and height of the analyzed image"
    )
    explanation_available: bool = Field(
        default=False,
        description="Whether visual or feature explanation (e.g. Grad-CAM) is available"
    )
    bounding_boxes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional object detection bounding boxes for disease lesions"
    )
    original_filename: str = Field(..., description="Sanitized original filename of the uploaded image")
    file_size_bytes: int = Field(..., description="Size of the uploaded file in bytes")
    mime_type: str = Field(..., description="MIME type of the image")
    created_at: datetime = Field(..., description="ISO-8601 timestamp when analysis was recorded")
    error_message: Optional[str] = Field(
        default=None,
        description="Safe error description if the analysis failed"
    )

    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    """Paginated list of historical fish image analyses."""
    total: int = Field(..., description="Total count of analyses in database")
    limit: int = Field(..., description="Maximum items requested in this page")
    offset: int = Field(..., description="Number of items skipped")
    items: List[AnalysisResponse] = Field(..., description="List of analysis records ordered newest first")


class ExplanationResponse(BaseModel):
    """Explainable AI (XAI) metadata for an analysis record."""
    analysis_id: int = Field(..., description="Identifier of the analysis")
    explanation_available: bool = Field(..., description="True if visual explanation was computed")
    method: Optional[str] = Field(
        default=None,
        description="Explanation method used (e.g., 'Grad-CAM', 'Eigen-CAM', 'Saliency')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Feature attribution or layer metadata"
    )
    explanation_image_url: Optional[str] = Field(
        default=None,
        description="Relative endpoint to download heatmap visual overlay if available"
    )
    message: Optional[str] = Field(
        default=None,
        description="Status description regarding explanation availability"
    )


class DeleteResponse(BaseModel):
    """Response confirming safe deletion of an analysis and its image file."""
    analysis_id: int = Field(..., description="Identifier of the deleted analysis")
    message: str = Field(..., description="Human-readable deletion confirmation")
    success: bool = Field(default=True, description="Indicates successful deletion")
