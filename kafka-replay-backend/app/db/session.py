"""Database session and engine management."""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None


async def init_db() -> None:
    """Initialize database engine and session factory."""
    global _engine, _async_session_factory

    logger.info("Initializing database connection", url=settings.DATABASE_URL)

    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
    )

    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    logger.info("Database connection initialized")


async def close_db() -> None:
    """Close database engine."""
    global _engine

    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


def get_session_factory() -> async_sessionmaker:
    """Get the async session factory."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory


async def get_db_session() -> AsyncSession:
    """
    Get a database session for dependency injection.
    
    Usage in FastAPI endpoints:
        async def my_endpoint(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
