"""Application configuration settings for AquaVigil Backend.

Loads environment variables from .env file or system environment with
sensible defaults tailored for local college project development.
"""

from pathlib import Path
from typing import List, Set
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class for AquaVigil backend service."""

    # Project Information
    PROJECT_NAME: str = "AquaVigil Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "AquaVigil — A Computer Vision Framework for Automated "
        "Fish Disease Detection in Aquaculture Systems"
    )
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    # Uses SQLite by default for zero-cost, friction-free local dev.
    # Can be switched to PostgreSQL via DATABASE_URL in .env.
    DATABASE_URL: str = "sqlite:///./storage/aquavigil.db"

    # Storage Settings
    STORAGE_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Cross-Origin Resource Sharing (CORS)
    # Comma-separated list of origins permitted to communicate with backend.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8081,http://10.0.2.2:8000"
    )

    # AI Model Configuration
    # Safe default: False. When False and no real model weights are present,
    # the API responds with status "model_not_configured" instead of fake results.
    ENABLE_MOCK_MODEL: bool = False
    MODEL_WEIGHTS_PATH: str = ""
    MODEL_DEVICE: str = "cpu"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated or json-formatted CORS origins into a list."""
        if not self.CORS_ORIGINS:
            return []
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert max upload size from megabytes to bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_mime_types(self) -> Set[str]:
        """Set of allowed image MIME types."""
        return {"image/jpeg", "image/png", "image/jpg"}

    @property
    def allowed_extensions(self) -> Set[str]:
        """Set of allowed image file extensions (lowercase with leading dot)."""
        return {".jpg", ".jpeg", ".png"}

    def get_storage_path(self) -> Path:
        """Ensure storage directory exists and return resolved Path object."""
        path = Path(self.STORAGE_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


# Instantiate singleton settings object
settings = Settings()
