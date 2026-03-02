"""
Data models for encoding detection and validation.

Defines Pydantic models for encoding results, validation results, and related data structures.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class EncodingType(str, Enum):
    """Supported encoding types."""

    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    UTF8_TEXT = "utf8_text"
    BINARY = "binary"
    UNKNOWN = "unknown"


class EncodingResult(BaseModel):
    """Result of encoding detection."""

    detected_encoding: EncodingType = Field(
        description="Detected encoding type"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) for the detection"
    )
    schema_id: Optional[int] = Field(
        default=None,
        description="Schema ID if Avro or Protobuf"
    )
    schema_version: Optional[int] = Field(
        default=None,
        description="Schema version if available"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if detection failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the encoding"
    )
    detection_method: str = Field(
        description="Method used to detect encoding (e.g., 'magic_byte', 'parse_attempt', 'heuristic')"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of detection"
    )


class ValidationResult(BaseModel):
    """Result of message validation."""

    is_valid: bool = Field(
        description="Whether the message is valid for the declared encoding"
    )
    encoding: EncodingType = Field(
        description="Encoding type that was validated"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if validation failed"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional validation details"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal validation warnings"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of validation"
    )


class DecodeResult(BaseModel):
    """Result of message decoding for display."""

    success: bool = Field(
        description="Whether decoding was successful"
    )
    content: Optional[Dict[str, Any] | str] = Field(
        default=None,
        description="Decoded content (dict for structured, str for text)"
    )
    encoding: EncodingType = Field(
        description="Encoding that was decoded"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if decoding failed"
    )
    preview: Optional[str] = Field(
        default=None,
        description="Preview of the content (truncated if needed)"
    )
    size_bytes: int = Field(
        description="Size of the original message in bytes"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of decoding"
    )


class SchemaMetadata(BaseModel):
    """Metadata about a schema from Schema Registry."""

    schema_id: int = Field(
        description="Schema ID"
    )
    schema_version: Optional[int] = Field(
        default=None,
        description="Schema version"
    )
    schema_type: str = Field(
        description="Schema type (AVRO, PROTOBUF, JSON, etc.)"
    )
    schema_subject: Optional[str] = Field(
        default=None,
        description="Subject/topic associated with the schema"
    )
    schema_content: str = Field(
        description="The actual schema definition"
    )
    references: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Schema references (for Protobuf, etc.)"
    )
    cached: bool = Field(
        default=False,
        description="Whether this metadata was retrieved from cache"
    )


class AvroMessage(BaseModel):
    """Parsed Avro message."""

    schema_id: int = Field(
        description="Avro schema ID"
    )
    data: Dict[str, Any] = Field(
        description="Decoded Avro data"
    )


class ProtobufMessage(BaseModel):
    """Parsed Protobuf message."""

    message_type: str = Field(
        description="Protobuf message type"
    )
    data: Dict[str, Any] = Field(
        description="Decoded Protobuf data"
    )


class EncodingDetectionConfig(BaseModel):
    """Configuration for encoding detection."""

    enable_json_detection: bool = Field(
        default=True,
        description="Enable JSON detection"
    )
    enable_avro_detection: bool = Field(
        default=True,
        description="Enable Avro detection"
    )
    enable_protobuf_detection: bool = Field(
        default=True,
        description="Enable Protobuf detection"
    )
    enable_utf8_detection: bool = Field(
        default=True,
        description="Enable UTF-8 text detection"
    )
    json_parse_timeout_ms: int = Field(
        default=100,
        description="Timeout for JSON parsing in milliseconds"
    )
    utf8_decode_timeout_ms: int = Field(
        default=50,
        description="Timeout for UTF-8 decoding in milliseconds"
    )
    min_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for accepting detection"
    )
    max_message_size_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum message size to process"
    )
