"""
Comprehensive replay service.

Orchestrates replay job management, execution, and progress tracking.
"""

import asyncio
import structlog
from typing import AsyncGenerator, Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import BaseMessagingAdapter
from app.sandbox.executor import ScriptExecutor

from .replay_models import (
    ReplayJobCreate,
    ReplayJobResponse,
    ReplayJobStatus,
    ReplayProgress,
    JobFilters,
)
from .replay_repository import ReplayJobRepository
from .replay_engine import ReplayEngine

logger = structlog.get_logger(__name__)


class ReplayService:
    """
    Comprehensive replay service for managing and executing replay jobs.

    Features:
    - Job CRUD operations
    - Async replay execution with progress streaming
    - Rate limiting
    - Script execution for message transformation
    - Dry-run mode
    - Comprehensive error handling
    """

    def __init__(
        self,
        messaging_adapter: BaseMessagingAdapter,
        session_factory,
        script_executor: Optional[ScriptExecutor] = None,
    ):
        """
        Initialize replay service.

        Args:
            messaging_adapter: Messaging adapter for Kafka operations.
            session_factory: Async SQLAlchemy session factory.
            script_executor: Optional script executor for transformations.
        """
        self.messaging_adapter = messaging_adapter
        self.session_factory = session_factory
        self.script_executor = script_executor
        self.engine = ReplayEngine(messaging_adapter, script_executor)
        self._active_jobs: Dict[UUID, asyncio.Task] = {}

    async def create_job(
        self,
        params: ReplayJobCreate,
    ) -> ReplayJobResponse:
        """
        Create a new replay job.

        Args:
            params: Job creation parameters.

        Returns:
            Created ReplayJobResponse.
        """
        async with self.session_factory() as session:
            try:
                repo = ReplayJobRepository(session)
                job = await repo.create(params)
                await repo.commit()

                logger.info(
                    "replay_job_created",
                    job_id=str(job.id),
                    source_topic=job.source_topic,
                )

                return job

            except Exception as e:
                await repo.rollback()
                logger.error("create_replay_job_failed", error=str(e))
                raise

    async def get_job(self, job_id: UUID) -> Optional[ReplayJobResponse]:
        """
        Get a replay job by ID.

        Args:
            job_id: Job ID.

        Returns:
            ReplayJobResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                repo = ReplayJobRepository(session)
                return await repo.get_by_id(job_id)

            except Exception as e:
                logger.error("get_replay_job_failed", job_id=str(job_id), error=str(e))
                raise

    async def list_jobs(
        self,
        filters: JobFilters,
    ) -> tuple[List[ReplayJobResponse], int]:
        """
        List replay jobs with filters.

        Args:
            filters: Job filters.

        Returns:
            Tuple of (jobs, total_count).
        """
        async with self.session_factory() as session:
            try:
                repo = ReplayJobRepository(session)
                return await repo.list_jobs(filters)

            except Exception as e:
                logger.error("list_replay_jobs_failed", error=str(e))
                raise

    async def start_job(
        self,
        job_id: UUID,
    ) -> AsyncGenerator[ReplayProgress, None]:
        """
        Start a replay job and stream progress.

        This is an async generator that yields progress updates as the job executes.

        Args:
            job_id: Job ID.

        Yields:
            ReplayProgress updates.
        """
        # Get job
        job = await self.get_job(job_id)
        if not job:
            logger.error("job_not_found", job_id=str(job_id))
            return

        # Check if already running
        if job.status == ReplayJobStatus.RUNNING:
            logger.warning("job_already_running", job_id=str(job_id))
            return

        try:
            # Update status to RUNNING
            async with self.session_factory() as session:
                repo = ReplayJobRepository(session)
                job = await repo.update_status(job_id, ReplayJobStatus.RUNNING)
                await repo.commit()

            logger.info("replay_job_started", job_id=str(job_id))

            # Execute replay and stream progress
            async for progress in self.engine.replay(job):
                # Update job progress in database
                async with self.session_factory() as session:
                    repo = ReplayJobRepository(session)
                    await repo.update_progress(
                        job_id,
                        progress.message_count,
                        progress.error_count,
                    )
                    await repo.commit()

                yield progress

                # Check if job should be paused
                current_job = await self.get_job(job_id)
                if current_job and current_job.status == ReplayJobStatus.PAUSED:
                    logger.info("replay_job_paused", job_id=str(job_id))
                    break

            # Update final status
            final_job = await self.get_job(job_id)
            if final_job and final_job.status == ReplayJobStatus.RUNNING:
                async with self.session_factory() as session:
                    repo = ReplayJobRepository(session)
                    await repo.update_status(job_id, ReplayJobStatus.COMPLETED)
                    await repo.commit()

        except Exception as e:
            logger.error("replay_job_execution_failed", job_id=str(job_id), error=str(e))

            # Mark job as failed
            try:
                async with self.session_factory() as session:
                    repo = ReplayJobRepository(session)
                    await repo.update_status(
                        job_id,
                        ReplayJobStatus.FAILED,
                        error_detail=str(e),
                    )
                    await repo.commit()
            except Exception as db_error:
                logger.error(
                    "failed_to_update_job_status",
                    job_id=str(job_id),
                    error=str(db_error),
                )

    async def pause_job(self, job_id: UUID) -> Optional[ReplayJobResponse]:
        """
        Pause a running replay job.

        Args:
            job_id: Job ID.

        Returns:
            Updated ReplayJobResponse or None if not found.
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                return None

            if job.status != ReplayJobStatus.RUNNING:
                logger.warning(
                    "cannot_pause_job",
                    job_id=str(job_id),
                    current_status=job.status.value,
                )
                return job

            async with self.session_factory() as session:
                repo = ReplayJobRepository(session)
                updated_job = await repo.update_status(job_id, ReplayJobStatus.PAUSED)
                await repo.commit()

                logger.info("replay_job_paused", job_id=str(job_id))

                return updated_job

        except Exception as e:
            logger.error("pause_replay_job_failed", job_id=str(job_id), error=str(e))
            raise

    async def cancel_job(self, job_id: UUID) -> Optional[ReplayJobResponse]:
        """
        Cancel a replay job.

        Args:
            job_id: Job ID.

        Returns:
            Updated ReplayJobResponse or None if not found.
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                return None

            if job.status in (ReplayJobStatus.COMPLETED, ReplayJobStatus.FAILED, ReplayJobStatus.CANCELLED):
                logger.warning(
                    "cannot_cancel_job",
                    job_id=str(job_id),
                    current_status=job.status.value,
                )
                return job

            async with self.session_factory() as session:
                repo = ReplayJobRepository(session)
                updated_job = await repo.update_status(job_id, ReplayJobStatus.CANCELLED)
                await repo.commit()

                logger.info("replay_job_cancelled", job_id=str(job_id))

                return updated_job

        except Exception as e:
            logger.error("cancel_replay_job_failed", job_id=str(job_id), error=str(e))
            raise

    async def resume_job(self, job_id: UUID) -> AsyncGenerator[ReplayProgress, None]:
        """
        Resume a paused replay job.

        Args:
            job_id: Job ID.

        Yields:
            ReplayProgress updates.
        """
        job = await self.get_job(job_id)
        if not job:
            logger.error("job_not_found", job_id=str(job_id))
            return

        if job.status != ReplayJobStatus.PAUSED:
            logger.warning(
                "cannot_resume_job",
                job_id=str(job_id),
                current_status=job.status.value,
            )
            return

        # Resume by starting from current position
        async for progress in self.start_job(job_id):
            yield progress

    async def get_job_stats(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a replay job.

        Args:
            job_id: Job ID.

        Returns:
            Dictionary with job statistics or None if not found.
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                return None

            total_messages = job.offset_end - job.offset_start + 1
            success_count = job.message_count - job.error_count
            success_rate = (
                (success_count / job.message_count * 100)
                if job.message_count > 0
                else 0
            )

            # Calculate duration
            duration = 0
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()

            avg_throughput = (
                job.message_count / duration if duration > 0 else 0
            )

            return {
                "job_id": str(job.id),
                "status": job.status.value,
                "total_messages": total_messages,
                "processed_messages": job.message_count,
                "error_messages": job.error_count,
                "success_rate": success_rate,
                "avg_throughput_msg_per_sec": avg_throughput,
                "total_duration_seconds": duration,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }

        except Exception as e:
            logger.error("get_job_stats_failed", job_id=str(job_id), error=str(e))
            raise
