"""
API response schemas and error models.

Defines all request/response models for the v1 API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Error Response Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: str = Field(description="Error message")
    code: str = Field(description="Error code (e.g., 'VALIDATION_ERROR')")
    detail: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Topic not found",
                "code": "TOPIC_NOT_FOUND",
                "detail": {"topic": "my-topic"},
            }
        }


# ============================================================================
# Topic Endpoints Response Models
# ============================================================================


class TopicInfo(BaseModel):
    """Information about a Kafka topic."""

    name: str = Field(description="Topic name")
    partitions: int = Field(description="Number of partitions")
    replication_factor: int = Field(description="Replication factor")
    is_internal: bool = Field(description="Whether topic is internal")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "user-events",
                "partitions": 3,
                "replication_factor": 1,
                "is_internal": False,
            }
        }


class TopicMetadata(BaseModel):
    """Detailed metadata for a Kafka topic."""

    name: str = Field(description="Topic name")
    partitions: int = Field(description="Number of partitions")
    replication_factor: int = Field(description="Replication factor")
    is_internal: bool = Field(description="Whether topic is internal")
    schema_id: Optional[int] = Field(default=None, description="Schema Registry ID")
    schema_subject: Optional[str] = Field(default=None, description="Schema subject name")
    schema_version: Optional[int] = Field(default=None, description="Schema version")
    leader_epochs: Dict[int, int] = Field(default_factory=dict, description="Leader epochs by partition")
    isr_replicas: Dict[int, List[int]] = Field(default_factory=dict, description="In-sync replicas by partition")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "user-events",
                "partitions": 3,
                "replication_factor": 1,
                "is_internal": False,
                "schema_id": 1,
                "schema_subject": "user-events-value",
                "schema_version": 2,
                "leader_epochs": {"0": 1, "1": 1, "2": 1},
                "isr_replicas": {"0": [0], "1": [1], "2": [2]},
            }
        }


class TopicsListResponse(BaseModel):
    """Response for listing topics."""

    topics: List[TopicInfo] = Field(description="List of topics")
    count: int = Field(description="Total number of topics")

    class Config:
        json_schema_extra = {
            "example": {
                "topics": [
                    {
                        "name": "user-events",
                        "partitions": 3,
                        "replication_factor": 1,
                        "is_internal": False,
                    }
                ],
                "count": 1,
            }
        }


class MessageRecord(BaseModel):
    """A single Kafka message."""

    partition: int = Field(description="Partition number")
    offset: int = Field(description="Message offset")
    timestamp: int = Field(description="Message timestamp (ms)")
    key: Optional[str] = Field(default=None, description="Message key")
    value: Dict[str, Any] = Field(description="Message value")
    headers: Dict[str, str] = Field(default_factory=dict, description="Message headers")
    encoding: str = Field(description="Detected encoding")

    class Config:
        json_schema_extra = {
            "example": {
                "partition": 0,
                "offset": 100,
                "timestamp": 1704067200000,
                "key": "user-123",
                "value": {"event": "login", "user_id": "123"},
                "headers": {"source": "web"},
                "encoding": "json",
            }
        }


class MessagesListResponse(BaseModel):
    """Response for browsing messages."""

    topic: str = Field(description="Topic name")
    partition: int = Field(description="Partition number")
    messages: List[MessageRecord] = Field(description="List of messages")
    total_available: int = Field(description="Total messages available in range")
    offset_start: int = Field(description="Start offset")
    offset_end: int = Field(description="End offset")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "user-events",
                "partition": 0,
                "messages": [],
                "total_available": 1000,
                "offset_start": 0,
                "offset_end": 100,
            }
        }


class EncodingDetectionResult(BaseModel):
    """Result of encoding detection for a topic."""

    topic: str = Field(description="Topic name")
    sample_size: int = Field(description="Number of messages sampled")
    detected_encodings: Dict[str, int] = Field(description="Encoding counts")
    primary_encoding: str = Field(description="Most common encoding")
    confidence: float = Field(description="Confidence score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "user-events",
                "sample_size": 100,
                "detected_encodings": {"json": 95, "binary": 5},
                "primary_encoding": "json",
                "confidence": 0.95,
            }
        }


# ============================================================================
# Replay Job Endpoints Response Models
# ============================================================================


class ReplayJobStatus(str, Enum):
    """Status of a replay job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReplayJobCreate(BaseModel):
    """Request to create a replay job."""

    source_topic: str = Field(description="Source topic")
    source_partition: int = Field(description="Source partition")
    offset_start: int = Field(description="Start offset")
    offset_end: int = Field(description="End offset")
    destination_topic: str = Field(description="Destination topic")
    replay_rate_per_sec: int = Field(default=1000, description="Messages per second")
    script_id: Optional[UUID] = Field(default=None, description="Optional enrichment script")
    dry_run: bool = Field(default=False, description="Dry-run mode (no produce)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "source_topic": "user-events",
                "source_partition": 0,
                "offset_start": 0,
                "offset_end": 1000,
                "destination_topic": "user-events-replay",
                "replay_rate_per_sec": 500,
                "script_id": None,
                "dry_run": False,
                "metadata": {"reason": "testing"},
            }
        }


class ReplayJobResponse(BaseModel):
    """Response model for a replay job."""

    id: UUID = Field(description="Job ID")
    source_topic: str = Field(description="Source topic")
    source_partition: int = Field(description="Source partition")
    offset_start: int = Field(description="Start offset")
    offset_end: int = Field(description="End offset")
    destination_topic: str = Field(description="Destination topic")
    status: ReplayJobStatus = Field(description="Job status")
    created_by: Optional[str] = Field(default=None, description="Creator")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    message_count: int = Field(default=0, description="Messages processed")
    error_count: int = Field(default=0, description="Errors encountered")
    replay_rate_per_sec: int = Field(description="Messages per second")
    script_id: Optional[UUID] = Field(default=None, description="Enrichment script")
    dry_run: bool = Field(description="Dry-run mode")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    error_detail: Optional[str] = Field(default=None, description="Error details if failed")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "source_topic": "user-events",
                "source_partition": 0,
                "offset_start": 0,
                "offset_end": 1000,
                "destination_topic": "user-events-replay",
                "status": "running",
                "created_by": "admin",
                "created_at": "2024-01-01T00:00:00Z",
                "started_at": "2024-01-01T00:00:01Z",
                "completed_at": None,
                "message_count": 500,
                "error_count": 0,
                "replay_rate_per_sec": 500,
                "script_id": None,
                "dry_run": False,
                "metadata": {"reason": "testing"},
                "error_detail": None,
            }
        }


class ReplayProgress(BaseModel):
    """Real-time progress update for a replay job."""

    job_id: UUID = Field(description="Job ID")
    status: ReplayJobStatus = Field(description="Current status")
    message_count: int = Field(description="Messages processed so far")
    error_count: int = Field(description="Errors so far")
    duration_ms: int = Field(description="Elapsed time (ms)")
    throughput: float = Field(description="Messages per second")
    estimated_remaining_ms: Optional[int] = Field(default=None, description="ETA (ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "message_count": 500,
                "error_count": 0,
                "duration_ms": 5000,
                "throughput": 100.0,
                "estimated_remaining_ms": 5000,
            }
        }


class ReplayJobsListResponse(BaseModel):
    """Response for listing replay jobs."""

    jobs: List[ReplayJobResponse] = Field(description="List of jobs")
    total: int = Field(description="Total number of jobs")
    limit: int = Field(description="Result limit")
    offset: int = Field(description="Result offset")

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 10,
                "limit": 50,
                "offset": 0,
            }
        }


class ReplayJobStats(BaseModel):
    """Statistics for a replay job."""

    job_id: UUID = Field(description="Job ID")
    total_messages: int = Field(description="Total messages to process")
    processed_messages: int = Field(description="Messages processed")
    error_count: int = Field(description="Errors encountered")
    success_rate: float = Field(description="Success rate (0-1)")
    duration_ms: int = Field(description="Total duration (ms)")
    throughput: float = Field(description="Messages per second")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_messages": 1000,
                "processed_messages": 1000,
                "error_count": 0,
                "success_rate": 1.0,
                "duration_ms": 10000,
                "throughput": 100.0,
            }
        }


# ============================================================================
# Script Endpoints Response Models
# ============================================================================


class ScriptStatus(str, Enum):
    """Status of a script."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ScriptCreate(BaseModel):
    """Request to create a script."""

    name: str = Field(description="Script name")
    description: Optional[str] = Field(default=None, description="Script description")
    code: str = Field(description="Python script code")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "add-timestamp",
                "description": "Adds current timestamp to messages",
                "code": "def transform(message, headers):\n    import time\n    message['timestamp'] = int(time.time() * 1000)\n    return message",
            }
        }


class ScriptResponse(BaseModel):
    """Response model for a script."""

    id: UUID = Field(description="Script ID")
    name: str = Field(description="Script name")
    description: Optional[str] = Field(default=None, description="Script description")
    code: str = Field(description="Script code")
    version: int = Field(description="Current version")
    status: ScriptStatus = Field(description="Script status")
    created_by: Optional[str] = Field(default=None, description="Creator")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Update timestamp")
    published_at: Optional[datetime] = Field(default=None, description="Publication timestamp")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "add-timestamp",
                "description": "Adds current timestamp to messages",
                "code": "def transform(message, headers):\n    import time\n    message['timestamp'] = int(time.time() * 1000)\n    return message",
                "version": 1,
                "status": "draft",
                "created_by": "admin",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "published_at": None,
                "archived_at": None,
            }
        }


class ScriptTestRequest(BaseModel):
    """Request to test a script."""

    payload: Dict[str, Any] = Field(description="Test message payload")
    headers: Dict[str, str] = Field(default_factory=dict, description="Test headers")

    class Config:
        json_schema_extra = {
            "example": {
                "payload": {"event": "login", "user_id": "123"},
                "headers": {"source": "web"},
            }
        }


class ScriptTestResult(BaseModel):
    """Result of testing a script."""

    success: bool = Field(description="Test success")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Transformed output")
    logs: str = Field(default="", description="Captured logs")
    duration_ms: int = Field(description="Execution time (ms)")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "output": {"event": "login", "user_id": "123", "timestamp": 1704067200000},
                "logs": "",
                "duration_ms": 10,
                "error": None,
            }
        }


class ScriptsListResponse(BaseModel):
    """Response for listing scripts."""

    scripts: List[ScriptResponse] = Field(description="List of scripts")
    total: int = Field(description="Total number of scripts")
    limit: int = Field(description="Result limit")
    offset: int = Field(description="Result offset")

    class Config:
        json_schema_extra = {
            "example": {
                "scripts": [],
                "total": 5,
                "limit": 50,
                "offset": 0,
            }
        }


# ============================================================================
# Health Check Response Models
# ============================================================================


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Response for health check."""

    status: HealthStatus = Field(description="Overall status")
    timestamp: datetime = Field(description="Check timestamp")
    services: Dict[str, str] = Field(description="Service-specific status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "services": {
                    "kafka": "healthy",
                    "postgres": "healthy",
                    "schema_registry": "healthy",
                },
            }
        }
