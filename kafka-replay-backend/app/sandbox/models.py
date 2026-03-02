"""
Script models and database schema.

Defines Pydantic models for scripts and database models for version management.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Enum as SQLEnum,
    UUID as SQLUUID,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ScriptStatus(str, Enum):
    """Script status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ScriptModel(Base):
    """SQLAlchemy model for scripts."""

    __tablename__ = "scripts"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(
        SQLEnum(ScriptStatus),
        default=ScriptStatus.DRAFT,
        nullable=False,
    )
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_name_version", "name", "version"),
        Index("idx_status_created", "status", "created_at"),
    )


class ScriptExecutionModel(Base):
    """SQLAlchemy model for script execution history."""

    __tablename__ = "script_executions"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    script_id = Column(SQLUUID(as_uuid=True), nullable=False, index=True)
    script_version = Column(Integer, nullable=False)
    job_id = Column(SQLUUID(as_uuid=True), nullable=True, index=True)
    success = Column(Integer, default=0, nullable=False)  # SQLite compatibility
    duration_ms = Column(Integer, nullable=False)
    error = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_script_created", "script_id", "created_at"),
        Index("idx_job_created", "job_id", "created_at"),
    )


class ScriptCreate(BaseModel):
    """Request model for creating a script."""

    name: str = Field(description="Script name")
    description: Optional[str] = Field(default=None, description="Script description")
    code: str = Field(description="Python script code")
    created_by: Optional[str] = Field(default=None, description="Creator")


class ScriptUpdate(BaseModel):
    """Request model for updating a script."""

    description: Optional[str] = Field(default=None)
    code: Optional[str] = Field(default=None)


class ScriptPublish(BaseModel):
    """Request model for publishing a script."""

    version: int = Field(description="Version to publish")


class ScriptResponse(BaseModel):
    """Response model for a script."""

    id: UUID = Field(description="Script ID")
    name: str = Field(description="Script name")
    description: Optional[str] = Field(description="Script description")
    code: str = Field(description="Script code")
    version: int = Field(description="Current version")
    status: ScriptStatus = Field(description="Script status")
    created_by: Optional[str] = Field(description="Creator")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Update timestamp")
    published_at: Optional[datetime] = Field(description="Publication timestamp")
    archived_at: Optional[datetime] = Field(description="Archive timestamp")

    class Config:
        from_attributes = True


class ScriptResult(BaseModel):
    """Result of script execution."""

    output: Dict[str, Any] = Field(description="Transformed message payload")
    logs: str = Field(description="Captured stdout/stderr")
    duration_ms: int = Field(description="Execution time in milliseconds")
    success: bool = Field(description="Execution success")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ScriptExecutionRecord(BaseModel):
    """Record of a script execution."""

    id: UUID = Field(description="Execution ID")
    script_id: UUID = Field(description="Script ID")
    script_version: int = Field(description="Script version")
    job_id: Optional[UUID] = Field(description="Associated job ID")
    success: bool = Field(description="Execution success")
    duration_ms: int = Field(description="Execution time")
    error: Optional[str] = Field(description="Error if failed")
    logs: Optional[str] = Field(description="Captured logs")
    created_at: datetime = Field(description="Execution timestamp")

    class Config:
        from_attributes = True
