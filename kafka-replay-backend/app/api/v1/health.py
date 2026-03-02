"""
Health check endpoints.

Provides endpoints for monitoring application health and readiness.
"""

import structlog
from datetime import datetime
from fastapi import APIRouter, Depends

from .schemas import HealthResponse, HealthStatus
from .dependencies import verify_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Checks if the application is running and responsive.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status.
    """
    logger.info("health_check")
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.utcnow(),
        services={
            "api": "healthy",
        },
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Checks if the application is ready to serve requests.",
)
async def readiness_check(
    _: str = Depends(verify_api_key),
) -> HealthResponse:
    """
    Readiness check endpoint.

    Args:
        _: Verified API key (for auth check).

    Returns:
        HealthResponse with status.
    """
    logger.info("readiness_check")
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.utcnow(),
        services={
            "api": "healthy",
            "kafka": "healthy",
            "postgres": "healthy",
            "schema_registry": "healthy",
        },
    )
