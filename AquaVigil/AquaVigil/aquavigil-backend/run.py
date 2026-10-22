"""AquaVigil Backend Server Runner.

Start local development server with:
    python run.py
"""

import sys
import uvicorn
from app.core.config import settings


def print_banner() -> None:
    """Print project banner and quickstart URLs."""
    banner = f"""
======================================================================
     _                    __     ___       _ _ 
    / \\   __ _ _   _  __ \\ \\   / (_) __ _(_) |
   / _ \\ / _` | | | |/ _` \\ \\ / /| |/ _` | | |
  / ___ \\ (_| | |_| | (_| |\\ V / | | (_| | | |
 /_/   \\_\\__, |\\__,_|\\__,_| \\_/  |_|\\__, |_|_|
            |_|                     |___/      
======================================================================
  Project     : {settings.PROJECT_NAME} (v{settings.VERSION})
  Environment : {settings.ENVIRONMENT}
  Database    : {settings.DATABASE_URL.split('@')[-1]}
  Storage Dir : {settings.STORAGE_DIR}
  Mock Mode   : {'ENABLED' if settings.ENABLE_MOCK_MODEL else 'DISABLED (Safe Mode)'}
----------------------------------------------------------------------
  Base URL    : http://{settings.HOST}:{settings.PORT}
  Health Check: http://{settings.HOST}:{settings.PORT}/health
  Swagger Docs: http://{settings.HOST}:{settings.PORT}/docs
  ReDoc Docs  : http://{settings.HOST}:{settings.PORT}/redoc
======================================================================
"""
    print(banner)


def main() -> None:
    """Launch Uvicorn server."""
    print_banner()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
