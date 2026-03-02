# Replay Service

This document provides an overview of the replay engine service for the Kafka replay tool backend.

## Overview

The replay service is responsible for managing and executing replay jobs. It handles the orchestration of consuming messages from a source topic, optionally transforming them via scripts, and producing them to a destination topic with rate limiting and progress tracking.

## Key Components

- **`replay_service.py`**: The main service class that provides a unified interface for job management and execution.
- **`replay_engine.py`**: Implements the core replay logic including rate limiting, progress streaming, and message transformation.
- **`replay_repository.py`**: Provides async database access for replay jobs using SQLAlchemy.
- **`replay_models.py`**: Contains all Pydantic models and SQLAlchemy ORM models for replay jobs.

## Features

- **Job State Management**: Replay jobs progress through states: PENDING → RUNNING → PAUSED | COMPLETED | FAILED | CANCELLED.
- **Progress Streaming**: The `start_job` method is an async generator that yields progress updates, enabling real-time monitoring via Server-Sent Events (SSE).
- **Rate Limiting**: Honors the `replay_rate_per_sec` parameter using `asyncio.sleep` to throttle message production.
- **Script Execution**: If a `script_id` is provided, each message is piped through a sandbox before production, enabling message transformation and enrichment.
- **Dry-Run Mode**: When `dry_run` is True, messages are decoded and transformed but never produced to the destination topic.
- **Error Handling**: On failure, the job is marked as FAILED with detailed error information; the service never crashes.

## Data Model

The `ReplayJob` database model includes:

| Field                | Type      | Description                                  |
| -------------------- | --------- | -------------------------------------------- |
| `id`                 | UUID      | Unique job identifier                        |
| `source_topic`       | String    | Source Kafka topic                           |
| `source_partition`   | Integer   | Source partition number                      |
| `offset_start`       | Integer   | Starting offset (inclusive)                  |
| `offset_end`         | Integer   | Ending offset (inclusive)                    |
| `destination_topic`  | String    | Destination Kafka topic                      |
| `status`             | Enum      | Current job status                           |
| `created_by`         | String    | User who created the job                     |
| `created_at`         | DateTime  | Job creation timestamp                       |
| `started_at`         | DateTime  | Job start timestamp                          |
| `completed_at`       | DateTime  | Job completion timestamp                     |
| `message_count`      | Integer   | Messages successfully processed              |
| `error_count`        | Integer   | Errors encountered                           |
| `replay_rate_per_sec`| Float     | Rate limit in messages per second            |
| `script_id`          | String    | Optional enrichment script ID                |
| `dry_run`            | Boolean   | Dry-run mode flag                            |
| `error_detail`       | String    | Error details if job failed                  |
| `metadata`           | JSON      | Additional metadata                          |

## Usage

The `ReplayService` should be instantiated once and used throughout the application. It requires a messaging adapter and an async SQLAlchemy session factory.

```python
# In your application startup
from app.services.replay_service import ReplayService
from app.adapters.kafka import KafkaAdapter

# Create service
replay_service = ReplayService(
    messaging_adapter=kafka_adapter,
    session_factory=async_session_factory,
    script_executor=script_executor,
)

# Create a replay job
job_params = ReplayJobCreate(
    source_topic="events",
    source_partition=0,
    offset_start=100,
    offset_end=200,
    destination_topic="events-replayed",
    replay_rate_per_sec=1000,
    dry_run=False,
)
job = await replay_service.create_job(job_params)

# Start the job and stream progress
async for progress in replay_service.start_job(job.id):
    print(f"Progress: {progress.progress_percent}%")

# Pause a running job
await replay_service.pause_job(job.id)

# Resume a paused job
async for progress in replay_service.resume_job(job.id):
    print(f"Progress: {progress.progress_percent}%")

# Get job statistics
stats = await replay_service.get_job_stats(job.id)
print(f"Success rate: {stats['success_rate']}%")
```

## Progress Streaming

The `start_job` method is an async generator that yields `ReplayProgress` updates. This is designed to be consumed by a Server-Sent Events (SSE) endpoint for real-time progress tracking in the frontend.

```python
@app.get("/api/v1/replays/{job_id}/progress")
async def stream_replay_progress(job_id: UUID):
    async def event_generator():
        async for progress in replay_service.start_job(job_id):
            yield f"data: {progress.model_dump_json()}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

## Error Handling

The service is designed to never crash due to message processing errors. If an error occurs during replay:

1. The error is logged with full context.
2. The error count is incremented.
3. The job continues processing subsequent messages.
4. If a critical error occurs (e.g., broker unavailable), the job is marked as FAILED with error details.

## Rate Limiting

Rate limiting is implemented using `asyncio.sleep` to throttle message production. The service calculates the expected time for processing a certain number of messages based on the `replay_rate_per_sec` parameter and sleeps if ahead of schedule.

This approach ensures that the service never hammers the broker and respects the configured rate limit.
