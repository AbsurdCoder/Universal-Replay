"""Application lifespan management (startup/shutdown events)."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.core.logging import get_logger
from app.db.session import init_db, close_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan() -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting up application")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
