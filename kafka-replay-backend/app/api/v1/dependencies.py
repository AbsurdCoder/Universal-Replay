"""
Authentication and dependency injection for API endpoints.

Provides API key validation and service dependencies.
"""

import structlog
from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import get_async_session
from app.adapters.kafka import KafkaAdapter
from app.services.encoding_service import EncodingService
from app.services.replay_service import ReplayService
from app.sandbox.service import ScriptSandboxService

logger = structlog.get_logger(__name__)

# Global service instances (initialized in app startup)
_kafka_adapter: Optional[KafkaAdapter] = None
_encoding_service: Optional[EncodingService] = None
_replay_service: Optional[ReplayService] = None
_script_service: Optional[ScriptSandboxService] = None


async def verify_api_key(
    x_api_key: str = Header(None),
    settings: Settings = Depends(lambda: Settings()),
) -> str:
    """
    Verify API key from X-API-Key header.

    Args:
        x_api_key: API key from header.
        settings: Application settings.

    Returns:
        The API key if valid.

    Raises:
        HTTPException: If API key is invalid or missing.
    """
    if not settings.API_KEYS:
        # If no API keys configured, allow all requests (development mode)
        logger.warning("no_api_keys_configured")
        return "default"

    if not x_api_key:
        logger.warning("missing_api_key")
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    if x_api_key not in settings.API_KEYS:
        logger.warning("invalid_api_key", key=x_api_key[:8])
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    logger.info("api_key_verified")
    return x_api_key


async def get_session(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncSession:
    """
    Get database session.

    Args:
        session: Async SQLAlchemy session.

    Returns:
        The session.
    """
    return session


async def get_kafka_adapter(
    _: str = Depends(verify_api_key),
) -> KafkaAdapter:
    """
    Get Kafka adapter instance.

    Args:
        _: Verified API key (for auth check).

    Returns:
        Kafka adapter instance.

    Raises:
        HTTPException: If adapter not initialized.
    """
    if not _kafka_adapter:
        logger.error("kafka_adapter_not_initialized")
        raise HTTPException(
            status_code=503,
            detail="Kafka adapter not initialized",
        )
    return _kafka_adapter


async def get_encoding_service(
    _: str = Depends(verify_api_key),
) -> EncodingService:
    """
    Get encoding service instance.

    Args:
        _: Verified API key (for auth check).

    Returns:
        Encoding service instance.

    Raises:
        HTTPException: If service not initialized.
    """
    if not _encoding_service:
        logger.error("encoding_service_not_initialized")
        raise HTTPException(
            status_code=503,
            detail="Encoding service not initialized",
        )
    return _encoding_service


async def get_replay_service(
    _: str = Depends(verify_api_key),
) -> ReplayService:
    """
    Get replay service instance.

    Args:
        _: Verified API key (for auth check).

    Returns:
        Replay service instance.

    Raises:
        HTTPException: If service not initialized.
    """
    if not _replay_service:
        logger.error("replay_service_not_initialized")
        raise HTTPException(
            status_code=503,
            detail="Replay service not initialized",
        )
    return _replay_service


async def get_script_service(
    _: str = Depends(verify_api_key),
) -> ScriptSandboxService:
    """
    Get script sandbox service instance.

    Args:
        _: Verified API key (for auth check).

    Returns:
        Script sandbox service instance.

    Raises:
        HTTPException: If service not initialized.
    """
    if not _script_service:
        logger.error("script_service_not_initialized")
        raise HTTPException(
            status_code=503,
            detail="Script sandbox service not initialized",
        )
    return _script_service


def set_kafka_adapter(adapter: KafkaAdapter) -> None:
    """Set the global Kafka adapter instance."""
    global _kafka_adapter
    _kafka_adapter = adapter


def set_encoding_service(service: EncodingService) -> None:
    """Set the global encoding service instance."""
    global _encoding_service
    _encoding_service = service


def set_replay_service(service: ReplayService) -> None:
    """Set the global replay service instance."""
    global _replay_service
    _replay_service = service


def set_script_service(service: ScriptSandboxService) -> None:
    """Set the global script sandbox service instance."""
    global _script_service
    _script_service = service
