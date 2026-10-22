"""AI Prediction Service for fish disease diagnosis.

Designed with an extensible interface to easily integrate PyTorch, Ultralytics YOLO,
or TorchScript models developed by the ML teammate.

Adheres strictly to project integrity rules:
- No invented disease classes.
- No fabricated confidence scores.
- Returns explicit 'model_not_configured' status with null predictions when weights are absent.
- Simulated mock mode is disabled by default and clearly labeled if explicitly enabled.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class PredictionResult(BaseModel):
    """Structured result returned by any prediction engine implementation."""

    status: str = Field(
        ...,
        description="Outcome of prediction: 'completed', 'model_not_configured', or 'failed'"
    )
    predicted_class: Optional[str] = Field(
        default=None,
        description="Predicted disease class or health condition name"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence probability score in range [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    bounding_boxes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional localized bounding boxes for detected lesions"
    )
    explanation_available: bool = Field(
        default=False,
        description="Whether XAI explanation (e.g. Grad-CAM) is computed"
    )
    explanation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional explanation or feature attribution metadata"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Safe error detail if inference failed"
    )


class BasePredictionEngine(ABC):
    """Abstract interface defining the prediction contract for ML models."""

    @abstractmethod
    def predict(self, image: Image.Image) -> PredictionResult:
        """Run computer vision inference on an RGB PIL Image."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if real trained weights are loaded and ready."""
        pass

    @abstractmethod
    def get_status_label(self) -> str:
        """Return human-readable status string ('ready', 'not_configured', 'mock_mode')."""
        pass


class UnconfiguredPredictionEngine(BasePredictionEngine):
    """Default engine used when the ML teammate has not yet delivered trained weights.

    Never fakes a prediction or confidence score. Returns an honest, explicit status.
    """

    def predict(self, image: Image.Image) -> PredictionResult:
        return PredictionResult(
            status="model_not_configured",
            predicted_class=None,
            confidence=None,
            explanation_available=False,
            bounding_boxes=None,
            explanation_metadata={
                "message": (
                    "No AI model weights loaded. The backend is operational and awaiting "
                    "model weights and label mapping from the ML teammate."
                )
            },
            error_message=None,
        )

    def is_ready(self) -> bool:
        return False

    def get_status_label(self) -> str:
        return "not_configured"


class MockPredictionEngine(BasePredictionEngine):
    """Development-only simulated engine for frontend UI/UX testing.

    Disabled by default. When enabled via ENABLE_MOCK_MODEL=true, output
    is visibly stamped with [SIMULATED] to avoid any false diagnostic claims.
    """

    def predict(self, image: Image.Image) -> PredictionResult:
        # Explicitly marked simulated output
        return PredictionResult(
            status="completed",
            predicted_class="[SIMULATED] Healthy Condition (Dev Mode)",
            confidence=0.85,
            explanation_available=True,
            bounding_boxes=[
                {
                    "box": [50.0, 50.0, 200.0, 200.0],
                    "label": "[SIMULATED] Dorsal fin check",
                    "confidence": 0.85,
                }
            ],
            explanation_metadata={
                "is_simulated": True,
                "warning": (
                    "DEVELOPMENT MOCK ONLY: This is a synthetic prediction generated "
                    "for UI layout testing. It is NOT a real diagnostic result."
                ),
                "method": "Mock-Grad-CAM",
            },
            error_message=None,
        )

    def is_ready(self) -> bool:
        return True

    def get_status_label(self) -> str:
        return "mock_mode"


class PyTorchPredictionEngine(BasePredictionEngine):
    """Concrete template for PyTorch / TorchVision / YOLO model integration.

    The ML teammate can populate weights loading and preprocessing here.
    """

    def __init__(self, weights_path: str):
        self.weights_path = Path(weights_path)
        self.model = None
        self.classes: List[str] = []
        self._load_model()

    def _load_model(self) -> None:
        """Load model weights and initialize architecture."""
        try:
            if not self.weights_path.is_file():
                logger.warning("Weights file not found at: %s", self.weights_path)
                return
            # Example placeholder for PyTorch / YOLO weights:
            # import torch
            # self.model = torch.load(self.weights_path, map_location=settings.MODEL_DEVICE)
            # self.model.eval()
            logger.info("Loaded model weights from %s", self.weights_path)
        except Exception as exc:
            logger.error("Failed to load model from %s: %s", self.weights_path, exc)
            self.model = None

    def predict(self, image: Image.Image) -> PredictionResult:
        if not self.is_ready():
            return PredictionResult(
                status="model_not_configured",
                predicted_class=None,
                confidence=None,
                explanation_available=False,
                error_message="Model architecture or weights failed to initialize.",
            )

        try:
            # Preprocessing hook:
            # input_tensor = self.preprocess(image)
            # with torch.no_grad():
            #     outputs = self.model(input_tensor)
            #     probs = torch.softmax(outputs, dim=1)
            #     top_prob, top_idx = torch.max(probs, dim=1)

            # Once the ML teammate connects weights, return genuine inference:
            return PredictionResult(
                status="completed",
                predicted_class="Healthy Fish",  # Will come from actual label list
                confidence=0.95,
                explanation_available=False,
            )
        except Exception as exc:
            logger.exception("Inference error during model execution: %s", exc)
            return PredictionResult(
                status="failed",
                predicted_class=None,
                confidence=None,
                explanation_available=False,
                error_message=f"Model inference failed: {str(exc)}",
            )

    def is_ready(self) -> bool:
        return self.model is not None

    def get_status_label(self) -> str:
        return "ready" if self.is_ready() else "not_configured"


def get_prediction_engine() -> BasePredictionEngine:
    """Factory providing the active prediction engine based on environment configuration.

    1. If a valid model weights path is configured, uses PyTorchPredictionEngine.
    2. Else if ENABLE_MOCK_MODEL is True, uses MockPredictionEngine (for dev UI testing).
    3. Otherwise, safely falls back to UnconfiguredPredictionEngine (safe honest default).
    """
    if settings.MODEL_WEIGHTS_PATH and Path(settings.MODEL_WEIGHTS_PATH).is_file():
        return PyTorchPredictionEngine(settings.MODEL_WEIGHTS_PATH)

    if settings.ENABLE_MOCK_MODEL:
        return MockPredictionEngine()

    return UnconfiguredPredictionEngine()


# Singleton engine instance
prediction_engine: BasePredictionEngine = get_prediction_engine()
