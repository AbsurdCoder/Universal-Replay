"""
Repository for replay job database operations.

Provides async database access for replay jobs.
"""

import structlog
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc

from .replay_models import (
    ReplayJobModel,
    ReplayJobStatus,
    ReplayJobCreate,
    ReplayJobResponse,
    JobFilters,
)

logger = structlog.get_logger(__name__)


class ReplayJobRepository:
    """Repository for replay job database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository.

        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def create(self, params: ReplayJobCreate) -> ReplayJobResponse:
        """
        Create a new replay job.

        Args:
            params: Job creation parameters.

        Returns:
            Created ReplayJobResponse.
        """
        try:
            job = ReplayJobModel(
                source_topic=params.source_topic,
                source_partition=params.source_partition,
                offset_start=params.offset_start,
                offset_end=params.offset_end,
                destination_topic=params.destination_topic,
                replay_rate_per_sec=params.replay_rate_per_sec,
                script_id=params.script_id,
                dry_run=1 if params.dry_run else 0,
                created_by=params.created_by,
                metadata=params.metadata,
                status=ReplayJobStatus.PENDING,
            )

            self.session.add(job)
            await self.session.flush()
            await self.session.refresh(job)

            logger.info(
                "replay_job_created",
                job_id=str(job.id),
                source_topic=job.source_topic,
            )

            return ReplayJobResponse.model_validate(job)

        except Exception as e:
            logger.error("create_replay_job_failed", error=str(e))
            raise

    async def get_by_id(self, job_id: UUID) -> Optional[ReplayJobResponse]:
        """
        Get a replay job by ID.

        Args:
            job_id: Job ID.

        Returns:
            ReplayJobResponse or None if not found.
        """
        try:
            stmt = select(ReplayJobModel).where(ReplayJobModel.id == job_id)
            result = await self.session.execute(stmt)
            job = result.scalar_one_or_none()

            if job:
                return ReplayJobResponse.model_validate(job)

            return None

        except Exception as e:
            logger.error("get_replay_job_failed", job_id=str(job_id), error=str(e))
            raise

    async def list_jobs(self, filters: JobFilters) -> tuple[List[ReplayJobResponse], int]:
        """
        List replay jobs with filters.

        Args:
            filters: Job filters.

        Returns:
            Tuple of (jobs, total_count).
        """
        try:
            # Build where clause
            conditions = []

            if filters.status:
                conditions.append(ReplayJobModel.status == filters.status)

            if filters.source_topic:
                conditions.append(ReplayJobModel.source_topic == filters.source_topic)

            if filters.created_by:
                conditions.append(ReplayJobModel.created_by == filters.created_by)

            where_clause = and_(*conditions) if conditions else None

            # Get total count
            count_stmt = select(ReplayJobModel)
            if where_clause is not None:
                count_stmt = count_stmt.where(where_clause)

            count_result = await self.session.execute(count_stmt)
            total_count = len(count_result.scalars().all())

            # Build query
            stmt = select(ReplayJobModel)
            if where_clause is not None:
                stmt = stmt.where(where_clause)

            # Order by
            if filters.order_direction == "asc":
                order_col = getattr(ReplayJobModel, filters.order_by)
                stmt = stmt.order_by(asc(order_col))
            else:
                order_col = getattr(ReplayJobModel, filters.order_by)
                stmt = stmt.order_by(desc(order_col))

            # Pagination
            stmt = stmt.limit(filters.limit).offset(filters.offset)

            result = await self.session.execute(stmt)
            jobs = result.scalars().all()

            return (
                [ReplayJobResponse.model_validate(job) for job in jobs],
                total_count,
            )

        except Exception as e:
            logger.error("list_replay_jobs_failed", error=str(e))
            raise

    async def update_status(
        self,
        job_id: UUID,
        status: ReplayJobStatus,
        error_detail: Optional[str] = None,
    ) -> Optional[ReplayJobResponse]:
        """
        Update job status.

        Args:
            job_id: Job ID.
            status: New status.
            error_detail: Optional error detail.

        Returns:
            Updated ReplayJobResponse or None if not found.
        """
        try:
            job = await self.get_by_id(job_id)
            if not job:
                return None

            stmt = select(ReplayJobModel).where(ReplayJobModel.id == job_id)
            result = await self.session.execute(stmt)
            db_job = result.scalar_one()

            db_job.status = status
            if error_detail:
                db_job.error_detail = error_detail

            if status == ReplayJobStatus.RUNNING:
                db_job.started_at = datetime.utcnow()
            elif status in (ReplayJobStatus.COMPLETED, ReplayJobStatus.FAILED, ReplayJobStatus.CANCELLED):
                db_job.completed_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(db_job)

            logger.info(
                "replay_job_status_updated",
                job_id=str(job_id),
                status=status.value,
            )

            return ReplayJobResponse.model_validate(db_job)

        except Exception as e:
            logger.error("update_replay_job_status_failed", job_id=str(job_id), error=str(e))
            raise

    async def update_progress(
        self,
        job_id: UUID,
        message_count: int,
        error_count: int,
    ) -> Optional[ReplayJobResponse]:
        """
        Update job progress.

        Args:
            job_id: Job ID.
            message_count: Messages processed.
            error_count: Errors encountered.

        Returns:
            Updated ReplayJobResponse or None if not found.
        """
        try:
            stmt = select(ReplayJobModel).where(ReplayJobModel.id == job_id)
            result = await self.session.execute(stmt)
            db_job = result.scalar_one_or_none()

            if not db_job:
                return None

            db_job.message_count = message_count
            db_job.error_count = error_count

            await self.session.flush()
            await self.session.refresh(db_job)

            return ReplayJobResponse.model_validate(db_job)

        except Exception as e:
            logger.error("update_replay_job_progress_failed", job_id=str(job_id), error=str(e))
            raise

    async def commit(self) -> None:
        """Commit transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self.session.rollback()
