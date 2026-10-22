"""SQLAlchemy ORM models representing the database schema for AquaVigil."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Analysis(Base):
    """Stores record of a fish image analysis request and resulting diagnosis."""

    __tablename__ = "analyses"

    # Primary key identifier
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Inference status & results
    # Status options: "pending", "completed", "failed", "model_not_configured"
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    predicted_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Optional object detection / localization bounding boxes
    bounding_boxes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # Model Explainability (Grad-CAM, saliency maps, etc.)
    explanation_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    explanation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Error logging (user-safe error description)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis(id={self.id}, "
            f"filename='{self.original_filename}', "
            f"status='{self.status}', "
            f"predicted_class='{self.predicted_class}', "
            f"confidence={self.confidence})>"
        )
