"""Fish disease image analysis and history management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Analysis
from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisResponse,
    DeleteResponse,
    ExplanationResponse,
    ImageDimensions,
)
from app.services.explanation_service import ExplanationService
from app.services.image_service import ImageService
from app.services.prediction_service import prediction_engine

router = APIRouter(prefix="/analyses", tags=["Analysis"])


def _to_analysis_response(record: Analysis) -> AnalysisResponse:
    """Helper to convert SQLAlchemy Analysis ORM record to AnalysisResponse schema."""
    dimensions = None
    if record.image_width and record.image_height:
        dimensions = ImageDimensions(width=record.image_width, height=record.image_height)

    return AnalysisResponse(
        analysis_id=record.id,
        status=record.status,
        predicted_class=record.predicted_class,
        confidence=record.confidence,
        image_dimensions=dimensions,
        explanation_available=record.explanation_available,
        bounding_boxes=record.bounding_boxes,
        original_filename=record.original_filename,
        file_size_bytes=record.file_size_bytes,
        mime_type=record.mime_type,
        created_at=record.created_at,
        error_message=record.error_message,
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze Fish Image",
    description=(
        "Upload a JPEG or PNG image of a fish for disease diagnosis. "
        "Validates image content, converts to RGB, saves locally, runs inference, "
        "and logs the complete transaction to the database."
    ),
)
async def analyze_fish_image(
    file: UploadFile = File(..., description="Fish image file (JPEG or PNG, max 10MB)"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Process an uploaded fish image and record diagnosis."""
    # 1. Sanitize original filename
    clean_filename = ImageService.sanitize_filename(file.filename)

    # 2. Validate format, magic bytes, dimensions, and size
    (
        processed_bytes,
        pil_image,
        stored_filename,
        mime_type,
        width,
        height,
    ) = await ImageService.validate_and_process_upload(file)

    # 3. Safely persist processed image to disk storage
    saved_path = ImageService.save_to_storage(stored_filename, processed_bytes)

    # 4. Execute AI disease diagnosis model
    prediction = prediction_engine.predict(pil_image)

    # 5. Store record in database
    analysis_record = Analysis(
        original_filename=clean_filename,
        stored_filename=stored_filename,
        file_path=str(saved_path),
        file_size_bytes=len(processed_bytes),
        mime_type=mime_type,
        image_width=width,
        image_height=height,
        status=prediction.status,
        predicted_class=prediction.predicted_class,
        confidence=prediction.confidence,
        bounding_boxes=prediction.bounding_boxes,
        explanation_available=prediction.explanation_available,
        explanation_metadata=prediction.explanation_metadata,
        error_message=prediction.error_message,
    )

    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    return _to_analysis_response(analysis_record)


@router.get(
    "",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Analysis History",
    description="Retrieve paginated analysis history records sorted newest first.",
)
def list_analyses(
    limit: int = Query(default=10, ge=1, le=100, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
) -> AnalysisListResponse:
    """Retrieve historical analyses with pagination."""
    total = db.scalar(select(func.count(Analysis.id))) or 0

    query = (
        select(Analysis)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .offset(offset)
        .limit(limit)
    )
    records = db.scalars(query).all()

    items = [_to_analysis_response(rec) for rec in records]

    return AnalysisListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis by ID",
    description="Retrieve details for a specific fish disease analysis record.",
)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Fetch single analysis record or return 404."""
    record = db.get(Analysis, analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record with ID {analysis_id} was not found.",
        )
    return _to_analysis_response(record)


@router.get(
    "/{analysis_id}/explanation",
    response_model=ExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Explanation",
    description="Retrieve explainability metadata (e.g. Grad-CAM) for a diagnosis.",
)
def get_analysis_explanation(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> ExplanationResponse:
    """Fetch visual explanation metadata or return 404/409."""
    record = db.get(Analysis, analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record with ID {analysis_id} was not found.",
        )
    return ExplanationService.get_explanation(record)


@router.get(
    "/{analysis_id}/image",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download Analysis Image",
    description="Stream the original uploaded fish image safely from server storage.",
)
def get_analysis_image(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream stored image file for rendering on frontend dashboards."""
    record = db.get(Analysis, analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record with ID {analysis_id} was not found.",
        )

    file_path = ImageService.get_file_path(record.stored_filename)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Physical image file for analysis ID {analysis_id} is missing on disk.",
        )

    return FileResponse(
        path=file_path,
        media_type=record.mime_type,
        filename=record.original_filename,
    )


@router.delete(
    "/{analysis_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Analysis Record",
    description="Safely delete an analysis record from the database and its associated image from storage.",
)
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Delete analysis record and clean up stored file."""
    record = db.get(Analysis, analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record with ID {analysis_id} was not found.",
        )

    # 1. Clean up stored file
    ImageService.delete_file(record.stored_filename)

    # 2. Delete database record
    db.delete(record)
    db.commit()

    return DeleteResponse(
        analysis_id=analysis_id,
        message=f"Analysis record {analysis_id} and associated image file were successfully deleted.",
        success=True,
    )
