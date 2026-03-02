"""
Script repository for version management.

Provides async database access for scripts and their execution history.
"""

import structlog
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from .models import (
    ScriptModel,
    ScriptExecutionModel,
    ScriptStatus,
    ScriptCreate,
    ScriptResponse,
    ScriptExecutionRecord,
)

logger = structlog.get_logger(__name__)


class ScriptRepository:
    """Repository for script database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository.

        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def create(self, params: ScriptCreate) -> ScriptResponse:
        """
        Create a new script.

        Args:
            params: Script creation parameters.

        Returns:
            Created ScriptResponse.
        """
        try:
            script = ScriptModel(
                name=params.name,
                description=params.description,
                code=params.code,
                version=1,
                status=ScriptStatus.DRAFT,
                created_by=params.created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.session.add(script)
            await self.session.flush()
            await self.session.refresh(script)

            logger.info(
                "script_created",
                script_id=str(script.id),
                name=script.name,
            )

            return ScriptResponse.model_validate(script)

        except Exception as e:
            logger.error("create_script_failed", error=str(e))
            raise

    async def get_by_id(self, script_id: UUID) -> Optional[ScriptResponse]:
        """
        Get a script by ID (latest version).

        Args:
            script_id: Script ID.

        Returns:
            ScriptResponse or None if not found.
        """
        try:
            stmt = select(ScriptModel).where(ScriptModel.id == script_id)
            result = await self.session.execute(stmt)
            script = result.scalar_one_or_none()

            if script:
                return ScriptResponse.model_validate(script)

            return None

        except Exception as e:
            logger.error("get_script_failed", script_id=str(script_id), error=str(e))
            raise

    async def get_by_name(self, name: str, version: Optional[int] = None) -> Optional[ScriptResponse]:
        """
        Get a script by name.

        Args:
            name: Script name.
            version: Optional specific version (defaults to latest).

        Returns:
            ScriptResponse or None if not found.
        """
        try:
            conditions = [ScriptModel.name == name]

            if version is not None:
                conditions.append(ScriptModel.version == version)

            stmt = select(ScriptModel).where(and_(*conditions))

            if version is None:
                stmt = stmt.order_by(desc(ScriptModel.version)).limit(1)

            result = await self.session.execute(stmt)
            script = result.scalar_one_or_none()

            if script:
                return ScriptResponse.model_validate(script)

            return None

        except Exception as e:
            logger.error("get_script_by_name_failed", name=name, error=str(e))
            raise

    async def list_scripts(
        self,
        status: Optional[ScriptStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ScriptResponse], int]:
        """
        List scripts with optional filtering.

        Args:
            status: Optional status filter.
            limit: Result limit.
            offset: Result offset.

        Returns:
            Tuple of (scripts, total_count).
        """
        try:
            # Build where clause
            conditions = []
            if status:
                conditions.append(ScriptModel.status == status)

            where_clause = and_(*conditions) if conditions else None

            # Get total count
            count_stmt = select(ScriptModel)
            if where_clause is not None:
                count_stmt = count_stmt.where(where_clause)

            count_result = await self.session.execute(count_stmt)
            total_count = len(count_result.scalars().all())

            # Get paginated results
            stmt = select(ScriptModel)
            if where_clause is not None:
                stmt = stmt.where(where_clause)

            stmt = stmt.order_by(desc(ScriptModel.created_at)).limit(limit).offset(offset)

            result = await self.session.execute(stmt)
            scripts = result.scalars().all()

            return (
                [ScriptResponse.model_validate(script) for script in scripts],
                total_count,
            )

        except Exception as e:
            logger.error("list_scripts_failed", error=str(e))
            raise

    async def update(self, script_id: UUID, code: str, description: Optional[str] = None) -> Optional[ScriptResponse]:
        """
        Update a script (creates new version).

        Args:
            script_id: Script ID.
            code: New code.
            description: Optional new description.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        try:
            # Get current script
            stmt = select(ScriptModel).where(ScriptModel.id == script_id)
            result = await self.session.execute(stmt)
            script = result.scalar_one_or_none()

            if not script:
                return None

            # Create new version
            new_version = script.version + 1
            new_script = ScriptModel(
                id=script_id,
                name=script.name,
                description=description if description is not None else script.description,
                code=code,
                version=new_version,
                status=ScriptStatus.DRAFT,
                created_by=script.created_by,
                created_at=script.created_at,
                updated_at=datetime.utcnow(),
            )

            self.session.add(new_script)
            await self.session.flush()
            await self.session.refresh(new_script)

            logger.info(
                "script_updated",
                script_id=str(script_id),
                new_version=new_version,
            )

            return ScriptResponse.model_validate(new_script)

        except Exception as e:
            logger.error("update_script_failed", script_id=str(script_id), error=str(e))
            raise

    async def publish(self, script_id: UUID, version: int) -> Optional[ScriptResponse]:
        """
        Publish a script version.

        Args:
            script_id: Script ID.
            version: Version to publish.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        try:
            stmt = select(ScriptModel).where(
                and_(
                    ScriptModel.id == script_id,
                    ScriptModel.version == version,
                )
            )
            result = await self.session.execute(stmt)
            script = result.scalar_one_or_none()

            if not script:
                return None

            script.status = ScriptStatus.PUBLISHED
            script.published_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(script)

            logger.info(
                "script_published",
                script_id=str(script_id),
                version=version,
            )

            return ScriptResponse.model_validate(script)

        except Exception as e:
            logger.error("publish_script_failed", script_id=str(script_id), error=str(e))
            raise

    async def archive(self, script_id: UUID) -> Optional[ScriptResponse]:
        """
        Archive a script.

        Args:
            script_id: Script ID.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        try:
            stmt = select(ScriptModel).where(ScriptModel.id == script_id)
            result = await self.session.execute(stmt)
            script = result.scalar_one_or_none()

            if not script:
                return None

            script.status = ScriptStatus.ARCHIVED
            script.archived_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(script)

            logger.info("script_archived", script_id=str(script_id))

            return ScriptResponse.model_validate(script)

        except Exception as e:
            logger.error("archive_script_failed", script_id=str(script_id), error=str(e))
            raise

    async def record_execution(
        self,
        script_id: UUID,
        script_version: int,
        success: bool,
        duration_ms: int,
        error: Optional[str] = None,
        logs: Optional[str] = None,
        job_id: Optional[UUID] = None,
    ) -> ScriptExecutionRecord:
        """
        Record a script execution.

        Args:
            script_id: Script ID.
            script_version: Script version.
            success: Execution success.
            duration_ms: Execution duration.
            error: Optional error message.
            logs: Optional captured logs.
            job_id: Optional associated job ID.

        Returns:
            ScriptExecutionRecord.
        """
        try:
            execution = ScriptExecutionModel(
                script_id=script_id,
                script_version=script_version,
                success=1 if success else 0,
                duration_ms=duration_ms,
                error=error,
                logs=logs,
                job_id=job_id,
                created_at=datetime.utcnow(),
            )

            self.session.add(execution)
            await self.session.flush()
            await self.session.refresh(execution)

            logger.info(
                "execution_recorded",
                script_id=str(script_id),
                version=script_version,
                success=success,
            )

            return ScriptExecutionRecord.model_validate(execution)

        except Exception as e:
            logger.error("record_execution_failed", script_id=str(script_id), error=str(e))
            raise

    async def get_execution_history(
        self,
        script_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ScriptExecutionRecord], int]:
        """
        Get execution history for a script.

        Args:
            script_id: Script ID.
            limit: Result limit.
            offset: Result offset.

        Returns:
            Tuple of (executions, total_count).
        """
        try:
            # Get total count
            count_stmt = select(ScriptExecutionModel).where(
                ScriptExecutionModel.script_id == script_id
            )
            count_result = await self.session.execute(count_stmt)
            total_count = len(count_result.scalars().all())

            # Get paginated results
            stmt = (
                select(ScriptExecutionModel)
                .where(ScriptExecutionModel.script_id == script_id)
                .order_by(desc(ScriptExecutionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            executions = result.scalars().all()

            return (
                [ScriptExecutionRecord.model_validate(e) for e in executions],
                total_count,
            )

        except Exception as e:
            logger.error("get_execution_history_failed", script_id=str(script_id), error=str(e))
            raise

    async def commit(self) -> None:
        """Commit transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self.session.rollback()
