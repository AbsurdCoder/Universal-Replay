"""
Script management endpoints.

Provides endpoints for uploading, managing, and testing enrichment scripts.
"""

import structlog
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.sandbox.service import ScriptSandboxService
from .schemas import (
    ErrorResponse,
    ScriptCreate,
    ScriptResponse,
    ScriptTestRequest,
    ScriptTestResult,
    ScriptsListResponse,
    ScriptStatus,
)
from .dependencies import get_script_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.post(
    "",
    response_model=ScriptResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Upload a script",
    description="Uploads a new enrichment script or creates a new version of an existing script.",
)
async def create_script(
    params: ScriptCreate,
    script_service: ScriptSandboxService = Depends(get_script_service),
) -> ScriptResponse:
    """
    Create a new script.

    Args:
        params: Script creation parameters.
        script_service: Script sandbox service.

    Returns:
        Created ScriptResponse.

    Raises:
        HTTPException: If script creation fails.
    """
    try:
        logger.info("creating_script", name=params.name)

        script = await script_service.create_script(params)

        logger.info("script_created", script_id=str(script.id), name=script.name)
        return script

    except ValueError as e:
        logger.warning("invalid_script", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid script: {str(e)}",
        )
    except Exception as e:
        logger.error("create_script_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to create script: {str(e)}",
        )


@router.get(
    "/{script_id}",
    response_model=ScriptResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Get script details",
    description="Retrieves the details of a specific script.",
)
async def get_script(
    script_id: UUID,
    script_service: ScriptSandboxService = Depends(get_script_service),
) -> ScriptResponse:
    """
    Get a script by ID.

    Args:
        script_id: Script ID.
        script_service: Script sandbox service.

    Returns:
        ScriptResponse with script details.

    Raises:
        HTTPException: If script not found.
    """
    try:
        logger.info("getting_script", script_id=str(script_id))

        script = await script_service.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

        return script

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_script_failed", script_id=str(script_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get script: {str(e)}",
        )


@router.post(
    "/{script_id}/test",
    response_model=ScriptTestResult,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Test a script",
    description="Tests a script against a sample payload to verify it works correctly.",
)
async def test_script(
    script_id: UUID,
    request: ScriptTestRequest,
    script_service: ScriptSandboxService = Depends(get_script_service),
) -> ScriptTestResult:
    """
    Test a script.

    Args:
        script_id: Script ID.
        request: Test request with payload and headers.
        script_service: Script sandbox service.

    Returns:
        ScriptTestResult with execution details.

    Raises:
        HTTPException: If script not found or test fails.
    """
    try:
        logger.info("testing_script", script_id=str(script_id))

        script = await script_service.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

        result = await script_service.execute_script(
            code=script.code,
            message=request.payload,
            headers=request.headers,
            script_id=script_id,
        )

        logger.info(
            "script_tested",
            script_id=str(script_id),
            success=result.success,
            duration_ms=result.duration_ms,
        )

        return ScriptTestResult(
            success=result.success,
            output=result.output if result.success else None,
            logs=result.logs,
            duration_ms=result.duration_ms,
            error=result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_script_failed", script_id=str(script_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to test script: {str(e)}",
        )


@router.get(
    "",
    response_model=ScriptsListResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="List scripts",
    description="Retrieves a paginated list of scripts with optional filtering by status.",
)
async def list_scripts(
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
    limit: int = Query(50, ge=1, le=1000, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    script_service: ScriptSandboxService = Depends(get_script_service),
) -> ScriptsListResponse:
    """
    List scripts.

    Args:
        status: Optional status filter.
        limit: Result limit.
        offset: Result offset.
        script_service: Script sandbox service.

    Returns:
        ScriptsListResponse with paginated scripts.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        logger.info("listing_scripts", status=status, limit=limit, offset=offset)

        # Parse status if provided
        script_status = None
        if status:
            try:
                script_status = ScriptStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}",
                )

        scripts, total = await script_service.list_scripts(
            status=script_status,
            limit=limit,
            offset=offset,
        )

        logger.info("scripts_listed", count=len(scripts), total=total)
        return ScriptsListResponse(
            scripts=scripts,
            total=total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_scripts_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to list scripts: {str(e)}",
        )
