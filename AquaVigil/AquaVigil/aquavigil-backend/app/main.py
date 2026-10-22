"""AquaVigil Backend — FastAPI Application Entrypoint.

Computer Vision Framework for Automated Fish Disease Detection in Aquaculture Systems.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.statistics import router as statistics_router
from app.core.config import settings
from app.db.database import init_db

# Configure standard logging format
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("aquavigil")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to handle startup and shutdown events."""
    logger.info("Initializing AquaVigil database tables...")
    init_db()
    # Ensure storage directories exist
    settings.get_storage_path()
    logger.info("Database and storage initialized. AquaVigil backend is ready.")
    yield
    logger.info("Shutting down AquaVigil backend service.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS Middleware
# Restricted to specified development origins by default to protect against unauthorized origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global fallback exception handler to prevent leaking sensitive tracebacks."""
    logger.exception("Unhandled server exception at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact the backend team.",
            "error_type": exc.__class__.__name__,
        },
    )


@app.get("/", tags=["Root"], summary="Root Information")
def root_info() -> dict:
    """Root endpoint welcoming developers and linking to API documentation."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "documentation": "/docs",
        "health_check": "/health",
        "api_v1_prefix": settings.API_V1_STR,
    }


# Register Health endpoint at root (/health) and API prefix (/api/v1/health)
app.include_router(health_router)
app.include_router(health_router, prefix=settings.API_V1_STR)

# Register Statistics router BEFORE Analysis router to ensure /analyses/stats is matched first
app.include_router(statistics_router, prefix=settings.API_V1_STR)

# Register Analysis router
app.include_router(analysis_router, prefix=settings.API_V1_STR)
