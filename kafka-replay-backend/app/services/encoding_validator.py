"""
Message validation logic for different encodings.

Validates messages against their declared encoding type.
"""

import json
import struct
import asyncio
import structlog
from typing import Optional

from .encoding_models import (
    EncodingType,
    ValidationResult,
)
from .schema_registry_client import SchemaRegistryClient

logger = structlog.get_logger(__name__)


class EncodingValidator:
    """Validates messages against their declared encoding type."""

    def __init__(
        self,
        schema_registry_client: Optional[SchemaRegistryClient] = None,
    ):
        """
        Initialize encoding validator.

        Args:
            schema_registry_client: Optional Schema Registry client.
        """
        self.schema_registry_client = schema_registry_client

    async def validate_message(
        self,
        raw_bytes: bytes,
        declared_encoding: str,
        topic: str,
    ) -> ValidationResult:
        """
        Validate a message against its declared encoding.

        Args:
            raw_bytes: Raw message bytes.
            declared_encoding: Declared encoding type.
            topic: Topic name.

        Returns:
            ValidationResult indicating whether message is valid.
        """
        try:
            # Parse encoding type
            try:
                encoding_type = EncodingType(declared_encoding.lower())
            except ValueError:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.UNKNOWN,
                    error=f"Unknown encoding type: {declared_encoding}",
                )

            # Route to appropriate validator
            if encoding_type == EncodingType.JSON:
                return await self._validate_json(raw_bytes)
            elif encoding_type == EncodingType.AVRO:
                return await self._validate_avro(raw_bytes, topic)
            elif encoding_type == EncodingType.PROTOBUF:
                return await self._validate_protobuf(raw_bytes, topic)
            elif encoding_type == EncodingType.UTF8_TEXT:
                return await self._validate_utf8(raw_bytes)
            elif encoding_type == EncodingType.BINARY:
                return await self._validate_binary(raw_bytes)
            else:
                return ValidationResult(
                    is_valid=False,
                    encoding=encoding_type,
                    error="Unsupported encoding type",
                )

        except Exception as e:
            logger.error("validation_error", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.UNKNOWN,
                error=f"Validation failed: {str(e)}",
            )

    async def _validate_json(self, raw_bytes: bytes) -> ValidationResult:
        """Validate JSON encoding."""
        try:
            # Decode as UTF-8
            try:
                text = raw_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.JSON,
                    error=f"Invalid UTF-8: {str(e)}",
                    details={"error_type": "utf8_decode_error"},
                )

            # Parse JSON
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.JSON,
                    error=f"Invalid JSON: {str(e)}",
                    details={
                        "error_type": "json_decode_error",
                        "line": e.lineno,
                        "column": e.colno,
                    },
                )

            logger.debug("json_validation_passed")

            return ValidationResult(
                is_valid=True,
                encoding=EncodingType.JSON,
                details={"size_bytes": len(raw_bytes)},
            )

        except Exception as e:
            logger.error("json_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.JSON,
                error=f"JSON validation failed: {str(e)}",
            )

    async def _validate_avro(
        self,
        raw_bytes: bytes,
        topic: str,
    ) -> ValidationResult:
        """Validate Avro encoding."""
        try:
            # Check magic byte
            if len(raw_bytes) < 5:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.AVRO,
                    error="Message too short for Avro (minimum 5 bytes)",
                    details={"size_bytes": len(raw_bytes)},
                )

            if raw_bytes[0] != 0x00:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.AVRO,
                    error=f"Invalid Avro magic byte: {hex(raw_bytes[0])} (expected 0x00)",
                    details={"magic_byte": hex(raw_bytes[0])},
                )

            # Extract schema ID
            schema_id = struct.unpack(">I", raw_bytes[1:5])[0]

            # Try to fetch schema from registry
            if self.schema_registry_client:
                schema = await self.schema_registry_client.get_schema_by_id(schema_id)
                if not schema:
                    return ValidationResult(
                        is_valid=False,
                        encoding=EncodingType.AVRO,
                        error=f"Schema ID {schema_id} not found in registry",
                        details={"schema_id": schema_id},
                    )

                logger.debug("avro_schema_found", schema_id=schema_id)

                return ValidationResult(
                    is_valid=True,
                    encoding=EncodingType.AVRO,
                    details={
                        "schema_id": schema_id,
                        "schema_type": schema.schema_type,
                        "size_bytes": len(raw_bytes),
                    },
                )

            # Schema registry not available, but magic byte is valid
            logger.warning(
                "avro_validation_without_registry",
                schema_id=schema_id,
            )

            return ValidationResult(
                is_valid=True,
                encoding=EncodingType.AVRO,
                details={"schema_id": schema_id, "size_bytes": len(raw_bytes)},
                warnings=["Schema not verified (registry unavailable)"],
            )

        except Exception as e:
            logger.error("avro_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.AVRO,
                error=f"Avro validation failed: {str(e)}",
            )

    async def _validate_protobuf(
        self,
        raw_bytes: bytes,
        topic: str,
    ) -> ValidationResult:
        """Validate Protobuf encoding."""
        try:
            # Protobuf validation is complex without descriptors
            # For now, we check if we can fetch schema from registry

            if not self.schema_registry_client:
                logger.warning("protobuf_validation_without_registry")

                return ValidationResult(
                    is_valid=True,
                    encoding=EncodingType.PROTOBUF,
                    details={"size_bytes": len(raw_bytes)},
                    warnings=["Protobuf schema not verified (registry unavailable)"],
                )

            # Try to get schema for topic
            schema = await self.schema_registry_client.get_latest_schema(topic)
            if not schema or schema.schema_type.upper() != "PROTOBUF":
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.PROTOBUF,
                    error=f"Protobuf schema not found for topic: {topic}",
                )

            logger.debug("protobuf_schema_found", topic=topic)

            return ValidationResult(
                is_valid=True,
                encoding=EncodingType.PROTOBUF,
                details={
                    "schema_id": schema.schema_id,
                    "schema_type": schema.schema_type,
                    "size_bytes": len(raw_bytes),
                },
            )

        except Exception as e:
            logger.error("protobuf_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.PROTOBUF,
                error=f"Protobuf validation failed: {str(e)}",
            )

    async def _validate_utf8(self, raw_bytes: bytes) -> ValidationResult:
        """Validate UTF-8 text encoding."""
        try:
            try:
                text = raw_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.UTF8_TEXT,
                    error=f"Invalid UTF-8: {str(e)}",
                    details={
                        "error_type": "utf8_decode_error",
                        "position": e.start,
                    },
                )

            logger.debug("utf8_validation_passed", length=len(text))

            return ValidationResult(
                is_valid=True,
                encoding=EncodingType.UTF8_TEXT,
                details={
                    "size_bytes": len(raw_bytes),
                    "text_length": len(text),
                },
            )

        except Exception as e:
            logger.error("utf8_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.UTF8_TEXT,
                error=f"UTF-8 validation failed: {str(e)}",
            )

    async def _validate_binary(self, raw_bytes: bytes) -> ValidationResult:
        """Validate binary encoding (always valid)."""
        logger.debug("binary_validation_passed")

        return ValidationResult(
            is_valid=True,
            encoding=EncodingType.BINARY,
            details={"size_bytes": len(raw_bytes)},
        )
