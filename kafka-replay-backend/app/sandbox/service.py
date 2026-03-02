"""
Comprehensive script sandbox service.

Orchestrates script management, execution, versioning, and history tracking.
"""

import structlog
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    ScriptCreate,
    ScriptResponse,
    ScriptResult,
    ScriptStatus,
    ScriptExecutionRecord,
)
from .runner import ScriptExecutor
from .repository import ScriptRepository
from .compiler import ScriptCompiler

logger = structlog.get_logger(__name__)


class ScriptSandboxService:
    """
    Comprehensive script sandbox service.

    Features:
    - Script management (CRUD, versioning)
    - Safe execution with RestrictedPython
    - Process-based isolation
    - Timeout enforcement
    - Execution history tracking
    - Version pinning for replay jobs
    """

    def __init__(
        self,
        session_factory,
        executor: Optional[ScriptExecutor] = None,
    ):
        """
        Initialize script sandbox service.

        Args:
            session_factory: Async SQLAlchemy session factory.
            executor: Optional script executor (created if not provided).
        """
        self.session_factory = session_factory
        self.executor = executor or ScriptExecutor(max_workers=4)
        self.compiler = ScriptCompiler()

    async def create_script(
        self,
        params: ScriptCreate,
    ) -> ScriptResponse:
        """
        Create a new script.

        Args:
            params: Script creation parameters.

        Returns:
            Created ScriptResponse.
        """
        async with self.session_factory() as session:
            try:
                # Validate syntax
                is_valid, error = self.compiler.validate_syntax(params.code)
                if not is_valid:
                    raise ValueError(f"Invalid script syntax: {error}")

                # Create script
                repo = ScriptRepository(session)
                script = await repo.create(params)
                await repo.commit()

                logger.info(
                    "script_created",
                    script_id=str(script.id),
                    name=script.name,
                )

                return script

            except Exception as e:
                await repo.rollback()
                logger.error("create_script_failed", error=str(e))
                raise

    async def get_script(self, script_id: UUID) -> Optional[ScriptResponse]:
        """
        Get a script by ID.

        Args:
            script_id: Script ID.

        Returns:
            ScriptResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                return await repo.get_by_id(script_id)

            except Exception as e:
                logger.error("get_script_failed", script_id=str(script_id), error=str(e))
                raise

    async def get_script_by_name(
        self,
        name: str,
        version: Optional[int] = None,
    ) -> Optional[ScriptResponse]:
        """
        Get a script by name.

        Args:
            name: Script name.
            version: Optional specific version.

        Returns:
            ScriptResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                return await repo.get_by_name(name, version)

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
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                return await repo.list_scripts(status, limit, offset)

            except Exception as e:
                logger.error("list_scripts_failed", error=str(e))
                raise

    async def update_script(
        self,
        script_id: UUID,
        code: str,
        description: Optional[str] = None,
    ) -> Optional[ScriptResponse]:
        """
        Update a script (creates new version).

        Args:
            script_id: Script ID.
            code: New code.
            description: Optional new description.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                # Validate syntax
                is_valid, error = self.compiler.validate_syntax(code)
                if not is_valid:
                    raise ValueError(f"Invalid script syntax: {error}")

                repo = ScriptRepository(session)
                script = await repo.update(script_id, code, description)
                await repo.commit()

                if script:
                    logger.info(
                        "script_updated",
                        script_id=str(script_id),
                        version=script.version,
                    )

                return script

            except Exception as e:
                await repo.rollback()
                logger.error("update_script_failed", script_id=str(script_id), error=str(e))
                raise

    async def publish_script(
        self,
        script_id: UUID,
        version: int,
    ) -> Optional[ScriptResponse]:
        """
        Publish a script version.

        Args:
            script_id: Script ID.
            version: Version to publish.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                script = await repo.publish(script_id, version)
                await repo.commit()

                if script:
                    logger.info(
                        "script_published",
                        script_id=str(script_id),
                        version=version,
                    )

                return script

            except Exception as e:
                await repo.rollback()
                logger.error("publish_script_failed", script_id=str(script_id), error=str(e))
                raise

    async def archive_script(self, script_id: UUID) -> Optional[ScriptResponse]:
        """
        Archive a script.

        Args:
            script_id: Script ID.

        Returns:
            Updated ScriptResponse or None if not found.
        """
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                script = await repo.archive(script_id)
                await repo.commit()

                if script:
                    logger.info("script_archived", script_id=str(script_id))

                return script

            except Exception as e:
                await repo.rollback()
                logger.error("archive_script_failed", script_id=str(script_id), error=str(e))
                raise

    async def execute_script(
        self,
        code: str,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        script_id: Optional[UUID] = None,
        job_id: Optional[UUID] = None,
    ) -> ScriptResult:
        """
        Execute a script safely.

        Args:
            code: Python script code.
            message: Message payload dict.
            headers: Optional message headers dict.
            script_id: Optional script ID for tracking.
            job_id: Optional job ID for tracking.

        Returns:
            ScriptResult with execution details.
        """
        if headers is None:
            headers = {}

        try:
            # Execute script
            result = await self.executor.execute(code, message, headers)

            # Record execution if script_id provided
            if script_id:
                async with self.session_factory() as session:
                    try:
                        repo = ScriptRepository(session)
                        await repo.record_execution(
                            script_id=script_id,
                            script_version=1,  # Version would be tracked separately
                            success=result.success,
                            duration_ms=result.duration_ms,
                            error=result.error,
                            logs=result.logs,
                            job_id=job_id,
                        )
                        await repo.commit()
                    except Exception as e:
                        logger.warning(
                            "failed_to_record_execution",
                            script_id=str(script_id),
                            error=str(e),
                        )

            return result

        except Exception as e:
            logger.error("execute_script_failed", error=str(e))
            return ScriptResult(
                output={},
                logs="",
                duration_ms=0,
                success=False,
                error=str(e),
            )

    async def execute_published_script(
        self,
        script_id: UUID,
        message: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        job_id: Optional[UUID] = None,
    ) -> ScriptResult:
        """
        Execute a published script by ID.

        Args:
            script_id: Script ID.
            message: Message payload dict.
            headers: Optional message headers dict.
            job_id: Optional job ID for tracking.

        Returns:
            ScriptResult with execution details.
        """
        try:
            # Get published script
            script = await self.get_script(script_id)
            if not script:
                return ScriptResult(
                    output={},
                    logs="",
                    duration_ms=0,
                    success=False,
                    error=f"Script not found: {script_id}",
                )

            if script.status != ScriptStatus.PUBLISHED:
                return ScriptResult(
                    output={},
                    logs="",
                    duration_ms=0,
                    success=False,
                    error=f"Script is not published: {script.status.value}",
                )

            # Execute script
            return await self.execute_script(
                code=script.code,
                message=message,
                headers=headers,
                script_id=script_id,
                job_id=job_id,
            )

        except Exception as e:
            logger.error("execute_published_script_failed", script_id=str(script_id), error=str(e))
            return ScriptResult(
                output={},
                logs="",
                duration_ms=0,
                success=False,
                error=str(e),
            )

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
        async with self.session_factory() as session:
            try:
                repo = ScriptRepository(session)
                return await repo.get_execution_history(script_id, limit, offset)

            except Exception as e:
                logger.error("get_execution_history_failed", script_id=str(script_id), error=str(e))
                raise

    def shutdown(self) -> None:
        """Shutdown the service."""
        self.executor.shutdown()
