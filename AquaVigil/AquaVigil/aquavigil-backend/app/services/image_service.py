"""Image handling and validation service for AquaVigil.

Provides secure file validation, streaming size limits, format checks,
color mode conversion, and safe filesystem storage without exposing internal paths.
"""

import io
import os
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


class ImageService:
    """Handles image upload validation, processing, and filesystem management."""

    # Maximum chunk size when reading stream to prevent RAM exhaustion
    CHUNK_SIZE = 64 * 1024  # 64 KB

    @staticmethod
    def sanitize_filename(filename: Optional[str]) -> str:
        """Sanitize client-provided filename to prevent path traversal or injection.

        Strips directory components and replaces unsafe characters.
        """
        if not filename:
            return "unnamed_fish_sample.jpg"
        # Extract base name only, remove directory paths
        base_name = os.path.basename(filename)
        # Remove null bytes, control characters, and keep only safe alphanumerics, dots, hyphens, underscores
        clean_name = re.sub(r"[^\w\.-]", "_", base_name).strip("._")
        return clean_name if clean_name else "sample.jpg"

    @classmethod
    async def validate_and_process_upload(
        cls, file: UploadFile
    ) -> Tuple[bytes, Image.Image, str, str, int, int]:
        """Validate uploaded file stream for size and genuine image content.

        Returns:
            Tuple of (processed_bytes, PIL_Image, stored_filename, mime_type, width, height)
        Raises:
            HTTPException 400: If file is missing or not a valid image.
            HTTPException 413: If file size exceeds MAX_UPLOAD_SIZE_MB.
            HTTPException 415: If MIME type or image format is unsupported.
        """
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No image file was provided in the request.",
            )

        # 1. Enforce content-type header check if present
        content_type = (file.content_type or "").lower().strip()
        if content_type and content_type not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported media type '{content_type}'. "
                    f"Allowed formats are JPEG and PNG."
                ),
            )

        # 2. Stream content with hard byte limit to avoid memory exhaustion
        total_bytes = 0
        chunks = []
        max_bytes = settings.max_upload_size_bytes

        while True:
            chunk = await file.read(cls.CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                    detail=(
                        f"Image size exceeds the maximum allowed limit of "
                        f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                    ),
                )
            chunks.append(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        raw_bytes = b"".join(chunks)

        # 3. Deep image content validation using Pillow (verifies real magic bytes)
        try:
            # First pass: verify structural integrity
            probe_img = Image.open(io.BytesIO(raw_bytes))
            actual_format = probe_img.format  # e.g., 'JPEG', 'PNG'
            probe_img.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is corrupted or not a valid image.",
            ) from exc

        # Ensure verified format matches allowed formats
        if actual_format not in {"JPEG", "PNG"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Invalid image format '{actual_format}'. "
                    "Only JPEG and PNG images are accepted."
                ),
            )

        # 4. Second pass: Load image data for conversion and dimensions
        # (Image.open must be called again because verify() consumes stream)
        img = Image.open(io.BytesIO(raw_bytes))
        width, height = img.size

        # Convert palette, grayscale, or RGBA images to standard RGB for vision models
        output_format = actual_format
        mime_type = "image/jpeg" if actual_format == "JPEG" else "image/png"
        extension = "jpg" if actual_format == "JPEG" else "png"

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Encode processed RGB image into output buffer
        out_buf = io.BytesIO()
        if output_format == "JPEG":
            img.save(out_buf, format="JPEG", quality=95)
        else:
            img.save(out_buf, format="PNG")
        processed_bytes = out_buf.getvalue()

        # Generate a cryptographically safe, unique filename
        stored_filename = f"{uuid.uuid4().hex}.{extension}"

        return processed_bytes, img, stored_filename, mime_type, width, height

    @classmethod
    def save_to_storage(cls, stored_filename: str, data: bytes) -> Path:
        """Write processed image bytes to local storage directory.

        Returns:
            Resolved absolute Path of saved file.
        """
        storage_dir = settings.get_storage_path()
        target_path = storage_dir / stored_filename
        target_path.write_bytes(data)
        return target_path

    @classmethod
    def get_file_path(cls, stored_filename: str) -> Optional[Path]:
        """Locate stored image file safely without allowing path escape."""
        storage_dir = settings.get_storage_path()
        target_path = (storage_dir / stored_filename).resolve()
        # Verify target is strictly within storage_dir
        if storage_dir in target_path.parents and target_path.is_file():
            return target_path
        return None

    @classmethod
    def delete_file(cls, stored_filename: str) -> bool:
        """Safely delete stored image file from filesystem."""
        path = cls.get_file_path(stored_filename)
        if path and path.exists():
            try:
                path.unlink()
                return True
            except OSError:
                return False
        return False
