"""Pydantic v2 models for request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ReplayJobStatusEnum(str, Enum):
    """Status enum for replay jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReplayJobFilterRequest(BaseModel):
    """Filtering criteria for replay jobs."""

    start_offset: Optional[int] = Field(None, description="Starting offset (inclusive)")
    end_offset: Optional[int] = Field(None, description="Ending offset (inclusive)")
    start_timestamp: Optional[datetime] = Field(None, description="Start time filter (ISO 8601)")
    end_timestamp: Optional[datetime] = Field(None, description="End time filter (ISO 8601)")
    key_pattern: Optional[str] = Field(None, description="Regex pattern for message keys")
    payload_filter: Optional[Dict[str, Any]] = Field(None, description="JSONPath-based payload filter")

    model_config = ConfigDict(json_schema_extra={"example": {"start_offset": 0, "end_offset": 1000}})


class CreateReplayJobRequest(BaseModel):
    """Request to create a new replay job."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    description: Optional[str] = Field(None, max_length=2000, description="Job description")
    source_topic: str = Field(..., description="Source Kafka topic")
    target_topic: str = Field(..., description="Target Kafka topic")
    filters: Optional[ReplayJobFilterRequest] = Field(None, description="Message filtering criteria")
    enrichment_script: Optional[str] = Field(None, description="Name of enrichment script")
    batch_size: int = Field(100, ge=1, le=10000, description="Batch size for processing")
    dry_run: bool = Field(False, description="Validate without replaying messages")
    created_by: Optional[str] = Field(None, description="User creating the job")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Daily Replay",
                "source_topic": "events",
                "target_topic": "events-replay",
                "batch_size": 100,
            }
        }
    )


class UpdateReplayJobRequest(BaseModel):
    """Request to update a replay job."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    enrichment_script: Optional[str] = None
    last_modified_by: Optional[str] = None


class ReplayJobProgressResponse(BaseModel):
    """Progress information for a replay job."""

    total_messages: int = Field(0, description="Total messages to replay")
    processed_messages: int = Field(0, description="Messages processed so far")
    failed_messages: int = Field(0, description="Messages that failed")
    skipped_messages: int = Field(0, description="Messages that were skipped")
    percentage: float = Field(0.0, ge=0, le=100, description="Progress percentage")

    model_config = ConfigDict(json_schema_extra={"example": {"total_messages": 1000, "processed_messages": 500, "percentage": 50.0}})


class ReplayJobStatisticsResponse(BaseModel):
    """Performance statistics for a replay job."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    throughput_msgs_per_sec: Optional[float] = None


class ReplayJobResponse(BaseModel):
    """Complete replay job response."""

    job_id: UUID = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Job name")
    description: Optional[str] = None
    source_topic: str = Field(..., description="Source topic")
    target_topic: str = Field(..., description="Target topic")
    status: ReplayJobStatusEnum = Field(..., description="Current job status")
    progress: ReplayJobProgressResponse = Field(..., description="Progress information")
    statistics: ReplayJobStatisticsResponse = Field(..., description="Performance statistics")
    enrichment_script: Optional[str] = None
    batch_size: int = Field(100, description="Batch size")
    dry_run: bool = Field(False, description="Dry run flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReplayJobListResponse(BaseModel):
    """List of replay jobs with pagination."""

    items: List[ReplayJobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    skip: int = Field(0, description="Number of items skipped")
    limit: int = Field(10, description="Number of items returned")

    model_config = ConfigDict(json_schema_extra={"example": {"items": [], "total": 0, "skip": 0, "limit": 10}})


class TopicMetadataResponse(BaseModel):
    """Metadata for a Kafka topic."""

    name: str = Field(..., description="Topic name")
    partitions: int = Field(..., description="Number of partitions")
    earliest_offset: int = Field(..., description="Earliest available offset")
    latest_offset: int = Field(..., description="Latest available offset")

    model_config = ConfigDict(json_schema_extra={"example": {"name": "events", "partitions": 3, "earliest_offset": 0, "latest_offset": 1000}})


class TopicListResponse(BaseModel):
    """List of Kafka topics."""

    topics: List[str] = Field(..., description="List of topic names")

    model_config = ConfigDict(json_schema_extra={"example": {"topics": ["events", "logs", "metrics"]}})


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "Resource not found", "error_code": "NOT_FOUND"}})


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy", "timestamp": "2024-02-23T10:30:00Z"}})
