"""
Replay job management endpoints.

Provides endpoints for creating, managing, and monitoring replay jobs.
"""

import structlog
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, StreamingResponse
from uuid import UUID

from app.services.replay_service import ReplayService
from .schemas import (
    ErrorResponse,
    ReplayJobCreate,
    ReplayJobResponse,
    ReplayJobsListResponse,
    ReplayJobStats,
    ReplayProgress,
)
from .dependencies import get_replay_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/replay/jobs", tags=["Replay Jobs"])


@router.post(
    "",
    response_model=ReplayJobResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Create a replay job",
    description="Creates a new replay job with specified source/destination topics and options.",
)
async def create_replay_job(
    params: ReplayJobCreate,
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobResponse:
    """
    Create a new replay job.

    Args:
        params: Job creation parameters.
        replay_service: Replay service.

    Returns:
        Created ReplayJobResponse.

    Raises:
        HTTPException: If job creation fails.
    """
    try:
        logger.info(
            "creating_replay_job",
            source_topic=params.source_topic,
            destination_topic=params.destination_topic,
        )

        job = await replay_service.create_job(params)

        logger.info("replay_job_created", job_id=str(job.id))
        return job

    except Exception as e:
        logger.error("create_replay_job_failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create replay job: {str(e)}",
        )


@router.post(
    "/{job_id}/start",
    response_model=ReplayJobResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Start a replay job",
    description="Starts execution of a replay job. Returns immediately; use /progress endpoint for real-time updates.",
)
async def start_replay_job(
    job_id: UUID,
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobResponse:
    """
    Start a replay job.

    Args:
        job_id: Job ID.
        replay_service: Replay service.

    Returns:
        Updated ReplayJobResponse.

    Raises:
        HTTPException: If job not found or start fails.
    """
    try:
        logger.info("starting_replay_job", job_id=str(job_id))

        # Start job in background
        job = await replay_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        # Create background task
        asyncio.create_task(replay_service.start_job_internal(job_id))

        logger.info("replay_job_started", job_id=str(job_id))
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error("start_replay_job_failed", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to start replay job: {str(e)}",
        )


@router.post(
    "/{job_id}/pause",
    response_model=ReplayJobResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Pause a replay job",
    description="Pauses an in-progress replay job. Can be resumed later.",
)
async def pause_replay_job(
    job_id: UUID,
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobResponse:
    """
    Pause a replay job.

    Args:
        job_id: Job ID.
        replay_service: Replay service.

    Returns:
        Updated ReplayJobResponse.

    Raises:
        HTTPException: If job not found or pause fails.
    """
    try:
        logger.info("pausing_replay_job", job_id=str(job_id))

        job = await replay_service.pause_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        logger.info("replay_job_paused", job_id=str(job_id))
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error("pause_replay_job_failed", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to pause replay job: {str(e)}",
        )


@router.post(
    "/{job_id}/cancel",
    response_model=ReplayJobResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Cancel a replay job",
    description="Cancels a replay job. Cannot be resumed.",
)
async def cancel_replay_job(
    job_id: UUID,
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobResponse:
    """
    Cancel a replay job.

    Args:
        job_id: Job ID.
        replay_service: Replay service.

    Returns:
        Updated ReplayJobResponse.

    Raises:
        HTTPException: If job not found or cancel fails.
    """
    try:
        logger.info("cancelling_replay_job", job_id=str(job_id))

        job = await replay_service.cancel_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        logger.info("replay_job_cancelled", job_id=str(job_id))
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cancel_replay_job_failed", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to cancel replay job: {str(e)}",
        )


@router.get(
    "/{job_id}",
    response_model=ReplayJobResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Get job status",
    description="Retrieves current status and statistics for a replay job.",
)
async def get_replay_job(
    job_id: UUID,
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobResponse:
    """
    Get replay job status.

    Args:
        job_id: Job ID.
        replay_service: Replay service.

    Returns:
        ReplayJobResponse with current status.

    Raises:
        HTTPException: If job not found.
    """
    try:
        logger.info("getting_replay_job", job_id=str(job_id))

        job = await replay_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_replay_job_failed", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get replay job: {str(e)}",
        )


@router.get(
    "/{job_id}/progress",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Stream job progress (SSE)",
    description="Server-Sent Events stream of real-time progress updates for a replay job.",
)
async def stream_replay_progress(
    job_id: UUID,
    replay_service: ReplayService = Depends(get_replay_service),
) -> StreamingResponse:
    """
    Stream replay job progress via SSE.

    Args:
        job_id: Job ID.
        replay_service: Replay service.

    Returns:
        StreamingResponse with SSE events.

    Raises:
        HTTPException: If job not found.
    """
    try:
        logger.info("streaming_replay_progress", job_id=str(job_id))

        # Verify job exists
        job = await replay_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        async def event_generator():
            """Generate SSE events for progress updates."""
            try:
                async for progress in replay_service.start_job(job_id):
                    # Format as SSE
                    event_data = progress.model_dump_json()
                    yield f"data: {event_data}\n\n"
                    await asyncio.sleep(0.1)  # Prevent tight loop

            except Exception as e:
                logger.error("progress_stream_error", job_id=str(job_id), error=str(e))
                yield f"data: {{'error': '{str(e)}'}}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stream_replay_progress_failed", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to stream progress: {str(e)}",
        )


@router.get(
    "",
    response_model=ReplayJobsListResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="List replay jobs",
    description="Retrieves a paginated list of replay jobs with optional filtering.",
)
async def list_replay_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    replay_service: ReplayService = Depends(get_replay_service),
) -> ReplayJobsListResponse:
    """
    List replay jobs.

    Args:
        status: Optional status filter.
        limit: Result limit.
        offset: Result offset.
        replay_service: Replay service.

    Returns:
        ReplayJobsListResponse with paginated jobs.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        logger.info("listing_replay_jobs", status=status, limit=limit, offset=offset)

        jobs, total = await replay_service.list_jobs(
            status=status,
            limit=limit,
            offset=offset,
        )

        logger.info("replay_jobs_listed", count=len(jobs), total=total)
        return ReplayJobsListResponse(
            jobs=jobs,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("list_replay_jobs_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to list replay jobs: {str(e)}",
        )
