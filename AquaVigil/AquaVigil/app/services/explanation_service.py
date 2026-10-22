"""Explanation Service for model interpretability (XAI).

Provides interfaces and handlers for Visual Explainability techniques such as
Grad-CAM, Eigen-CAM, and Saliency Maps to highlight disease lesion regions on fish.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status

from app.db.models import Analysis
from app.schemas.analysis import ExplanationResponse


class ExplanationService:
    """Manages retrieval and generation of model explanations."""

    @staticmethod
    def get_explanation(analysis: Analysis) -> ExplanationResponse:
        """Retrieve explanation details for a given analysis record.

        Raises:
            HTTPException 409: If analysis completed without generating an explanation.
        """
        if not analysis.explanation_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"No visual explanation (e.g., Grad-CAM) is available for analysis ID {analysis.id}. "
                    "Explanations require a trained model with feature attribution layers enabled."
                ),
            )

        metadata = analysis.explanation_metadata or {}
        method = metadata.get("method", "Grad-CAM")

        explanation_url: Optional[str] = None
        if analysis.explanation_path:
            explanation_url = f"/api/v1/analyses/{analysis.id}/explanation/image"

        return ExplanationResponse(
            analysis_id=analysis.id,
            explanation_available=True,
            method=method,
            metadata=metadata,
            explanation_image_url=explanation_url,
            message="Visual explanation metadata successfully retrieved.",
        )
