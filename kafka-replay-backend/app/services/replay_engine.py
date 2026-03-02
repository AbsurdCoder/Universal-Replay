"""
Replay engine with rate limiting and progress streaming.

Handles the core replay logic: consuming from source, transforming, and producing to destination.
"""

import asyncio
import structlog
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from time import time

from app.adapters.base import BaseMessagingAdapter
from app.sandbox.executor import ScriptExecutor

from .replay_models import (
    ReplayJobResponse,
    ReplayJobStatus,
    ReplayProgress,
)

logger = structlog.get_logger(__name__)


class ReplayEngine:
    """
    Replay engine for consuming, transforming, and producing messages.

    Features:
    - Rate limiting via asyncio.sleep
    - Progress streaming via async generator
    - Script execution for message transformation
    - Dry-run mode (decode/transform but don't produce)
    - Comprehensive error handling
    """

    def __init__(
        self,
        messaging_adapter: BaseMessagingAdapter,
        script_executor: Optional[ScriptExecutor] = None,
    ):
        """
        Initialize replay engine.

        Args:
            messaging_adapter: Messaging adapter for Kafka operations.
            script_executor: Optional script executor for transformations.
        """
        self.messaging_adapter = messaging_adapter
        self.script_executor = script_executor

    async def replay(
        self,
        job: ReplayJobResponse,
    ) -> AsyncGenerator[ReplayProgress, None]:
        """
        Execute a replay job and stream progress.

        This is an async generator that yields progress updates as messages are processed.

        Args:
            job: Replay job configuration.

        Yields:
            ReplayProgress updates.
        """
        start_time = time()
        message_count = 0
        error_count = 0
        current_offset = job.offset_start

        try:
            logger.info(
                "replay_started",
                job_id=str(job.id),
                source_topic=job.source_topic,
                destination_topic=job.destination_topic,
            )

            # Calculate total messages
            total_messages = job.offset_end - job.offset_start + 1

            # Consume messages from source topic
            async for raw_message in self.messaging_adapter.consume_messages(
                topic=job.source_topic,
                partition=job.source_partition,
                offset_start=job.offset_start,
                offset_end=job.offset_end,
                max_messages=total_messages,
            ):
                try:
                    current_offset = raw_message.offset

                    # Apply rate limiting
                    await self._apply_rate_limit(
                        job.replay_rate_per_sec,
                        message_count,
                        start_time,
                    )

                    # Transform message if script provided
                    transformed_message = raw_message
                    if job.script_id and self.script_executor:
                        try:
                            transformed_message = await self._transform_message(
                                raw_message,
                                job.script_id,
                            )
                        except Exception as e:
                            logger.warning(
                                "message_transformation_failed",
                                job_id=str(job.id),
                                offset=raw_message.offset,
                                error=str(e),
                            )
                            error_count += 1
                            continue

                    # Produce to destination (unless dry-run)
                    if not job.dry_run:
                        try:
                            await self.messaging_adapter.produce_messages(
                                topic=job.destination_topic,
                                messages=[transformed_message],
                                headers={
                                    "x-replay-source-offset": str(raw_message.offset),
                                    "x-replay-timestamp": datetime.utcnow().isoformat(),
                                    "x-replay-job-id": str(job.id),
                                },
                            )
                        except Exception as e:
                            logger.warning(
                                "message_produce_failed",
                                job_id=str(job.id),
                                offset=raw_message.offset,
                                error=str(e),
                            )
                            error_count += 1
                            continue

                    message_count += 1

                    # Yield progress update
                    elapsed = time() - start_time
                    throughput = message_count / elapsed if elapsed > 0 else 0

                    remaining_messages = total_messages - message_count
                    estimated_remaining = (
                        remaining_messages / job.replay_rate_per_sec
                        if job.replay_rate_per_sec > 0
                        else None
                    )

                    progress = ReplayProgress(
                        job_id=job.id,
                        status=ReplayJobStatus.RUNNING,
                        message_count=message_count,
                        error_count=error_count,
                        current_offset=current_offset,
                        total_messages=total_messages,
                        progress_percent=(message_count / total_messages * 100)
                        if total_messages > 0
                        else 0,
                        elapsed_seconds=elapsed,
                        estimated_remaining_seconds=estimated_remaining,
                        throughput_msg_per_sec=throughput,
                        timestamp=datetime.utcnow(),
                    )

                    yield progress

                except Exception as e:
                    logger.error(
                        "replay_message_processing_error",
                        job_id=str(job.id),
                        offset=current_offset,
                        error=str(e),
                    )
                    error_count += 1

            # Final progress update
            elapsed = time() - start_time
            throughput = message_count / elapsed if elapsed > 0 else 0

            final_progress = ReplayProgress(
                job_id=job.id,
                status=ReplayJobStatus.COMPLETED,
                message_count=message_count,
                error_count=error_count,
                current_offset=current_offset,
                total_messages=total_messages,
                progress_percent=100.0,
                elapsed_seconds=elapsed,
                estimated_remaining_seconds=0,
                throughput_msg_per_sec=throughput,
                timestamp=datetime.utcnow(),
            )

            yield final_progress

            logger.info(
                "replay_completed",
                job_id=str(job.id),
                message_count=message_count,
                error_count=error_count,
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            logger.error(
                "replay_failed",
                job_id=str(job.id),
                error=str(e),
            )

            # Yield error progress
            elapsed = time() - start_time
            error_progress = ReplayProgress(
                job_id=job.id,
                status=ReplayJobStatus.FAILED,
                message_count=message_count,
                error_count=error_count + 1,
                current_offset=current_offset,
                total_messages=total_messages,
                progress_percent=(message_count / total_messages * 100)
                if total_messages > 0
                else 0,
                elapsed_seconds=elapsed,
                estimated_remaining_seconds=None,
                throughput_msg_per_sec=0,
                timestamp=datetime.utcnow(),
            )

            yield error_progress

    async def _apply_rate_limit(
        self,
        rate_per_sec: float,
        message_count: int,
        start_time: float,
    ) -> None:
        """
        Apply rate limiting using asyncio.sleep.

        Args:
            rate_per_sec: Target rate in messages per second.
            message_count: Messages processed so far.
            start_time: Start time of replay.
        """
        if rate_per_sec <= 0:
            return

        # Calculate expected time for this many messages
        expected_time = message_count / rate_per_sec
        actual_time = time() - start_time

        # Sleep if we're ahead of schedule
        if actual_time < expected_time:
            sleep_time = expected_time - actual_time
            await asyncio.sleep(sleep_time)

    async def _transform_message(
        self,
        raw_message: Any,
        script_id: str,
    ) -> Any:
        """
        Transform a message using a script.

        Args:
            raw_message: Raw message to transform.
            script_id: Script ID to use for transformation.

        Returns:
            Transformed message.
        """
        if not self.script_executor:
            return raw_message

        try:
            # Execute script on message
            result = await self.script_executor.execute(
                script_id=script_id,
                input_data=raw_message.model_dump() if hasattr(raw_message, "model_dump") else raw_message,
            )

            # Update message value with result
            if isinstance(result, dict) and "value" in result:
                raw_message.value = result["value"]

            return raw_message

        except Exception as e:
            logger.error(
                "script_execution_failed",
                script_id=script_id,
                error=str(e),
            )
            raise
