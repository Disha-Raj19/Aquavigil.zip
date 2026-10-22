"""Pytest configuration and test fixtures for AquaVigil Backend.

Configures an isolated temporary database and temporary upload directory
so that test runs never alter development data or filesystem files.
"""

import io
import shutil
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test database and upload storage."""
    temp_path = Path(tempfile.mkdtemp(prefix="aquavigil_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="session")
def test_engine(test_temp_dir: Path):
    """Create a dedicated SQLite database engine for testing."""
    db_file = test_temp_dir / "test_aquavigil.db"
    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine, test_temp_dir: Path, monkeypatch) -> Generator[Session, None, None]:
    """Provide a clean, isolated database session per test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    # Point storage directory to temp folder
    temp_upload_dir = test_temp_dir / "uploads"
    temp_upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "STORAGE_DIR", str(temp_upload_dir))

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide FastAPI TestClient wired to the isolated test database session."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Generate a valid in-memory JPEG test image (120x80 RGB)."""
    img = Image.new("RGB", (120, 80), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Generate a valid in-memory PNG test image (150x100 RGBA)."""
    img = Image.new("RGBA", (150, 100), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def corrupted_image_bytes() -> bytes:
    """Return fake file bytes that pretend to be an image but are not."""
    return b"Not an image at all, just plain text pretending to be a fish picture."
