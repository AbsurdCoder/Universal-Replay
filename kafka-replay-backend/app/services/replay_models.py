"""
Replay job models and schemas.

Defines Pydantic models for replay job requests/responses and database models.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Enum as SQLEnum,
    JSON,
    UUID as SQLUUID,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ReplayJobStatus(str, Enum):
    """Replay job status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReplayJobModel(Base):
    """SQLAlchemy model for replay jobs."""

    __tablename__ = "replay_jobs"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_topic = Column(String(255), nullable=False, index=True)
    source_partition = Column(Integer, nullable=False)
    offset_start = Column(Integer, nullable=False)
    offset_end = Column(Integer, nullable=False)
    destination_topic = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(ReplayJobStatus),
        default=ReplayJobStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    replay_rate_per_sec = Column(Float, default=1000.0, nullable=False)
    script_id = Column(String(255), nullable=True)
    dry_run = Column(Integer, default=0, nullable=False)  # SQLite compatibility
    error_detail = Column(String(1024), nullable=True)
    metadata = Column(JSON, default={}, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
        Index("idx_source_topic_partition", "source_topic", "source_partition"),
    )


class ReplayJobCreate(BaseModel):
    """Request model for creating a replay job."""

    source_topic: str = Field(description="Source topic name")
    source_partition: int = Field(description="Source partition number")
    offset_start: int = Field(description="Starting offset (inclusive)")
    offset_end: int = Field(description="Ending offset (inclusive)")
    destination_topic: str = Field(description="Destination topic name")
    replay_rate_per_sec: float = Field(
        default=1000.0,
        description="Rate limit: messages per second",
    )
    script_id: Optional[str] = Field(
        default=None,
        description="Optional enrichment script ID",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, decode and transform but do not produce",
    )
    created_by: Optional[str] = Field(
        default=None,
        description="User who created the job",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class ReplayJobUpdate(BaseModel):
    """Request model for updating a replay job."""

    status: Optional[ReplayJobStatus] = Field(default=None)
    replay_rate_per_sec: Optional[float] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class ReplayJobResponse(BaseModel):
    """Response model for a replay job."""

    id: UUID = Field(description="Job ID")
    source_topic: str = Field(description="Source topic")
    source_partition: int = Field(description="Source partition")
    offset_start: int = Field(description="Starting offset")
    offset_end: int = Field(description="Ending offset")
    destination_topic: str = Field(description="Destination topic")
    status: ReplayJobStatus = Field(description="Current status")
    created_by: Optional[str] = Field(description="Creator")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(description="Start timestamp")
    completed_at: Optional[datetime] = Field(description="Completion timestamp")
    message_count: int = Field(description="Messages processed")
    error_count: int = Field(description="Errors encountered")
    replay_rate_per_sec: float = Field(description="Rate limit")
    script_id: Optional[str] = Field(description="Script ID")
    dry_run: bool = Field(description="Dry-run mode")
    error_detail: Optional[str] = Field(description="Error details")
    metadata: Dict[str, Any] = Field(description="Additional metadata")

    class Config:
        from_attributes = True


class JobFilters(BaseModel):
    """Filters for listing replay jobs."""

    status: Optional[ReplayJobStatus] = Field(default=None)
    source_topic: Optional[str] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="created_at", pattern="^(created_at|status|message_count)$")
    order_direction: str = Field(default="desc", pattern="^(asc|desc)$")


class ReplayProgress(BaseModel):
    """Progress update for a replay job."""

    job_id: UUID = Field(description="Job ID")
    status: ReplayJobStatus = Field(description="Current status")
    message_count: int = Field(description="Messages processed so far")
    error_count: int = Field(description="Errors so far")
    current_offset: int = Field(description="Current offset being processed")
    total_messages: int = Field(description="Total messages to process")
    progress_percent: float = Field(
        description="Progress percentage (0-100)",
        ge=0.0,
        le=100.0,
    )
    elapsed_seconds: float = Field(description="Elapsed time in seconds")
    estimated_remaining_seconds: Optional[float] = Field(
        description="Estimated time remaining"
    )
    throughput_msg_per_sec: float = Field(
        description="Current throughput in messages per second"
    )
    timestamp: datetime = Field(description="Update timestamp")


class ReplayJobStats(BaseModel):
    """Statistics for a replay job."""

    job_id: UUID = Field(description="Job ID")
    total_messages: int = Field(description="Total messages in range")
    processed_messages: int = Field(description="Successfully processed")
    error_messages: int = Field(description="Failed messages")
    success_rate: float = Field(description="Success rate percentage")
    avg_throughput_msg_per_sec: float = Field(description="Average throughput")
    total_duration_seconds: float = Field(description="Total duration")
    status: ReplayJobStatus = Field(description="Final status")
