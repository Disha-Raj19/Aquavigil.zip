"""SQLAlchemy database engine and session configuration for AquaVigil.

Configures connection to SQLite for local development or PostgreSQL for
production/staging environments based on the DATABASE_URL setting.
"""

from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# Ensure parent directory exists for SQLite database file
if settings.DATABASE_URL.startswith("sqlite"):
    # e.g., sqlite:///./storage/aquavigil.db -> ./storage/aquavigil.db
    db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path_str != ":memory:":
        db_path = Path(db_path_str).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )

# Session factory for DB transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional SQLAlchemy session.
    
    Guarantees session closure upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables on application startup."""
    # Import models to ensure they are registered with Base.metadata
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
