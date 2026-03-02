"""Database models for replay jobs and related data."""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from app.db.base import BaseModel


class ReplayJobStatus(str, PyEnum):
    """Status enum for replay jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReplayJob(BaseModel):
    """Model for tracking replay job state in database."""

    __tablename__ = "replay_jobs"

    # Identifiers
    job_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Kafka configuration
    source_topic = Column(String(255), nullable=False, index=True)
    target_topic = Column(String(255), nullable=False)

    # Filtering and processing
    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)
    start_timestamp = Column(DateTime, nullable=True)
    end_timestamp = Column(DateTime, nullable=True)
    key_pattern = Column(String(255), nullable=True)
    payload_filter = Column(JSON, nullable=True)

    # Enrichment
    enrichment_script = Column(String(255), nullable=True)

    # Configuration
    batch_size = Column(Integer, default=100, nullable=False)
    dry_run = Column(Boolean, default=False, nullable=False)

    # Status and progress
    status = Column(Enum(ReplayJobStatus), default=ReplayJobStatus.PENDING, nullable=False, index=True)
    total_messages = Column(Integer, default=0, nullable=False)
    processed_messages = Column(Integer, default=0, nullable=False)
    failed_messages = Column(Integer, default=0, nullable=False)
    skipped_messages = Column(Integer, default=0, nullable=False)

    # Performance metrics
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    throughput_msgs_per_sec = Column(Float, nullable=True)

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)

    # User information
    created_by = Column(String(255), nullable=True)
    last_modified_by = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<ReplayJob(job_id={self.job_id}, status={self.status})>"
