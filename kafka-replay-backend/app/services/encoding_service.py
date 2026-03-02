"""
Comprehensive encoding detection and validation service.

Combines detection, validation, and decoding logic into a single service.
"""

import structlog
from typing import Optional, Dict, Any, Union

from .encoding_models import (
    EncodingType,
    EncodingResult,
    ValidationResult,
    DecodeResult,
    EncodingDetectionConfig,
)
from .schema_registry_client import SchemaRegistryClient
from .encoding_detector import EncodingDetector
from .encoding_validator import EncodingValidator
from .encoding_decoder import EncodingDecoder

logger = structlog.get_logger(__name__)


class EncodingService:
    """
    Comprehensive encoding detection, validation, and decoding service.

    Provides a unified interface for:
    - Detecting message encoding (JSON, Avro, Protobuf, UTF-8, Binary)
    - Validating messages against declared encoding
    - Decoding messages for display
    """

    def __init__(
        self,
        schema_registry_url: Optional[str] = None,
        schema_registry_timeout: float = 10.0,
        cache_ttl_seconds: int = 60,
        cache_max_size: int = 1000,
        detection_config: Optional[EncodingDetectionConfig] = None,
        max_preview_length: int = 500,
    ):
        """
        Initialize encoding service.

        Args:
            schema_registry_url: URL of Schema Registry (optional).
            schema_registry_timeout: Timeout for Schema Registry requests.
            cache_ttl_seconds: Cache TTL in seconds.
            cache_max_size: Maximum cache size.
            detection_config: Optional detection configuration.
            max_preview_length: Maximum preview length.
        """
        # Initialize Schema Registry client if URL provided
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        if schema_registry_url:
            self.schema_registry_client = SchemaRegistryClient(
                base_url=schema_registry_url,
                timeout_seconds=schema_registry_timeout,
                cache_ttl_seconds=cache_ttl_seconds,
                cache_max_size=cache_max_size,
            )

        # Initialize detection, validation, and decoding components
        self.detector = EncodingDetector(
            schema_registry_client=self.schema_registry_client,
            config=detection_config or EncodingDetectionConfig(),
        )

        self.validator = EncodingValidator(
            schema_registry_client=self.schema_registry_client,
        )

        self.decoder = EncodingDecoder(
            schema_registry_client=self.schema_registry_client,
            max_preview_length=max_preview_length,
        )

    async def connect(self) -> None:
        """
        Connect to Schema Registry.

        Should be called during application startup.
        """
        if self.schema_registry_client:
            await self.schema_registry_client.connect()
            logger.info("encoding_service_connected")

    async def disconnect(self) -> None:
        """
        Disconnect from Schema Registry.

        Should be called during application shutdown.
        """
        if self.schema_registry_client:
            await self.schema_registry_client.disconnect()
            logger.info("encoding_service_disconnected")

    async def detect_encoding(
        self,
        raw_bytes: bytes,
        topic: str,
    ) -> EncodingResult:
        """
        Detect the encoding of a message.

        Uses layered heuristics:
        1. Avro magic byte (0x00)
        2. JSON parsing
        3. Schema Registry lookup
        4. UTF-8 text
        5. Binary fallback

        Args:
            raw_bytes: Raw message bytes.
            topic: Topic name (used for Schema Registry lookup).

        Returns:
            EncodingResult with detected encoding and confidence.
        """
        try:
            logger.debug("detecting_encoding", topic=topic, size=len(raw_bytes))

            result = await self.detector.detect_encoding(raw_bytes, topic)

            logger.info(
                "encoding_detected",
                topic=topic,
                encoding=result.detected_encoding,
                confidence=result.confidence,
                method=result.detection_method,
            )

            return result

        except Exception as e:
            logger.error("encoding_detection_failed", error=str(e))
            return EncodingResult(
                detected_encoding=EncodingType.UNKNOWN,
                confidence=0.0,
                detection_method="error",
                error=f"Detection failed: {str(e)}",
            )

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
            logger.debug(
                "validating_message",
                topic=topic,
                encoding=declared_encoding,
                size=len(raw_bytes),
            )

            result = await self.validator.validate_message(
                raw_bytes,
                declared_encoding,
                topic,
            )

            logger.info(
                "message_validated",
                topic=topic,
                encoding=declared_encoding,
                is_valid=result.is_valid,
            )

            return result

        except Exception as e:
            logger.error("message_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=False,
                encoding=EncodingType.UNKNOWN,
                error=f"Validation failed: {str(e)}",
            )

    async def decode_for_display(
        self,
        raw_bytes: bytes,
        encoding_result: EncodingResult,
    ) -> DecodeResult:
        """
        Decode a message for display.

        Args:
            raw_bytes: Raw message bytes.
            encoding_result: EncodingResult from detection.

        Returns:
            DecodeResult with decoded content.
        """
        try:
            logger.debug(
                "decoding_for_display",
                encoding=encoding_result.detected_encoding,
                size=len(raw_bytes),
            )

            result = await self.decoder.decode_for_display(raw_bytes, encoding_result)

            logger.info(
                "message_decoded",
                encoding=encoding_result.detected_encoding,
                success=result.success,
            )

            return result

        except Exception as e:
            logger.error("message_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=encoding_result.detected_encoding,
                error=f"Decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def detect_and_validate(
        self,
        raw_bytes: bytes,
        declared_encoding: Optional[str] = None,
        topic: str = "unknown",
    ) -> tuple[EncodingResult, ValidationResult]:
        """
        Detect encoding and validate against declared encoding (if provided).

        Args:
            raw_bytes: Raw message bytes.
            declared_encoding: Optional declared encoding to validate against.
            topic: Topic name.

        Returns:
            Tuple of (EncodingResult, ValidationResult).
        """
        try:
            # Detect encoding
            detected = await self.detect_encoding(raw_bytes, topic)

            # Validate if declared encoding provided
            if declared_encoding:
                validated = await self.validate_message(
                    raw_bytes,
                    declared_encoding,
                    topic,
                )
            else:
                # Use detected encoding for validation
                validated = await self.validate_message(
                    raw_bytes,
                    detected.detected_encoding.value,
                    topic,
                )

            return detected, validated

        except Exception as e:
            logger.error("detect_and_validate_failed", error=str(e))
            return (
                EncodingResult(
                    detected_encoding=EncodingType.UNKNOWN,
                    confidence=0.0,
                    error=str(e),
                    detection_method="error",
                ),
                ValidationResult(
                    is_valid=False,
                    encoding=EncodingType.UNKNOWN,
                    error=str(e),
                ),
            )

    async def process_message(
        self,
        raw_bytes: bytes,
        topic: str = "unknown",
        declared_encoding: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a message: detect, validate, and decode.

        Args:
            raw_bytes: Raw message bytes.
            topic: Topic name.
            declared_encoding: Optional declared encoding.

        Returns:
            Dictionary with detection, validation, and decoding results.
        """
        try:
            # Detect and validate
            detected, validated = await self.detect_and_validate(
                raw_bytes,
                declared_encoding,
                topic,
            )

            # Decode for display
            decoded = await self.decode_for_display(raw_bytes, detected)

            return {
                "detection": detected.model_dump(),
                "validation": validated.model_dump(),
                "decoding": decoded.model_dump(),
                "summary": {
                    "detected_encoding": detected.detected_encoding.value,
                    "is_valid": validated.is_valid,
                    "can_decode": decoded.success,
                    "message_size": len(raw_bytes),
                },
            }

        except Exception as e:
            logger.error("message_processing_failed", error=str(e))
            return {
                "error": str(e),
                "message_size": len(raw_bytes),
            }

    async def health_check(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            if self.schema_registry_client:
                return await self.schema_registry_client.health_check()
            return True
        except Exception as e:
            logger.warning("health_check_failed", error=str(e))
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        if self.schema_registry_client:
            return self.schema_registry_client.get_cache_stats()
        return {}

    def clear_cache(self) -> None:
        """Clear all caches."""
        if self.schema_registry_client:
            self.schema_registry_client.clear_cache()
            logger.info("cache_cleared")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
